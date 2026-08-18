"""Explicit PyTorch training loop for the Stage 04 baseline."""

from __future__ import annotations

from collections import Counter
import math
from pathlib import Path
import random
import time
from typing import Mapping

import numpy as np
import pandas as pd

from .evaluation import metric_bundle, mean_per_target_macro_f1
from .modeling import PairCollator, PairDataset, load_tokenizer_and_model, ordered_labels, save_checkpoint_support_files


def seed_everything(seed: int) -> None:
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)
    if hasattr(torch.backends, "cudnn"):
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True


def sampling_weights(frame: pd.DataFrame, max_relative_weight: float) -> np.ndarray:
    """Use 1/sqrt(target x label frequency), capped relative to the minimum."""
    frequencies = frame.groupby(["target", "label"]).size().to_dict()
    raw = np.array([
        1.0 / math.sqrt(frequencies[(target, label)])
        for target, label in zip(frame["target"], frame["label"])
    ], dtype=float)
    floor = float(raw.min()) if len(raw) else 1.0
    return np.minimum(raw, floor * float(max_relative_weight))


def _device_metadata(torch: object) -> tuple[object, dict[str, object]]:
    if torch.cuda.is_available():
        device = torch.device("cuda")
        index = torch.cuda.current_device()
        details = {
            "device": str(device),
            "cuda_available": True,
            "cuda_version": torch.version.cuda,
            "gpu_name": torch.cuda.get_device_name(index),
            "gpu_count": torch.cuda.device_count(),
        }
    else:
        device = torch.device("cpu")
        details = {
            "device": str(device),
            "cuda_available": False,
            "cuda_version": None,
            "gpu_name": None,
            "gpu_count": 0,
        }
    return device, details


def _validation_pass(
    model: object,
    loader: object,
    frame: pd.DataFrame,
    labels: list[str],
    device: object,
) -> tuple[float, list[str], dict[str, float | int]]:
    import torch

    losses = []
    predictions: list[str] = []
    model.eval()
    with torch.no_grad():
        for batch in loader:
            batch.pop("example_index")
            inputs = {key: value.to(device) for key, value in batch.items()}
            output = model(**inputs)
            losses.append(float(output.loss.detach().cpu()))
            predictions.extend(labels[index] for index in output.logits.argmax(dim=-1).detach().cpu().tolist())
    metrics, _ = metric_bundle(frame["label"], predictions, labels)
    metrics["mean_per_target_macro_f1"] = mean_per_target_macro_f1(
        frame["label"], predictions, frame["target"], labels,
    )
    return float(np.mean(losses)) if losses else float("nan"), predictions, metrics


def train_model(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    config: Mapping[str, object],
    checkpoint_dir: Path,
) -> dict[str, object]:
    """Train and select a checkpoint only by validation weak-label agreement."""
    import torch
    from torch.utils.data import DataLoader, WeightedRandomSampler
    from transformers import get_linear_schedule_with_warmup

    seed = int(config["seed"])
    seed_everything(seed)
    tokenizer, model, resolved_revision = load_tokenizer_and_model(config)
    label2id = {str(key): int(value) for key, value in config["labels"]["label2id"].items()}
    labels = ordered_labels(label2id)
    training = config["training"]
    device, hardware = _device_metadata(torch)
    model.to(device)
    train_dataset = PairDataset(train, tokenizer, label2id, int(config["tokenization"]["max_length"]))
    validation_dataset = PairDataset(validation, tokenizer, label2id, int(config["tokenization"]["max_length"]))
    weights = sampling_weights(train, float(config["sampling"]["max_relative_weight"]))
    generator = torch.Generator().manual_seed(seed)
    sampler = WeightedRandomSampler(
        torch.as_tensor(weights, dtype=torch.double),
        num_samples=len(train_dataset),
        replacement=True,
        generator=generator,
    )
    train_loader = DataLoader(
        train_dataset,
        batch_size=int(training["train_batch_size"]),
        sampler=sampler,
        collate_fn=PairCollator(tokenizer),
    )
    validation_loader = DataLoader(
        validation_dataset,
        batch_size=int(training["eval_batch_size"]),
        shuffle=False,
        collate_fn=PairCollator(tokenizer),
    )
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(training["learning_rate"]),
        weight_decay=float(training["weight_decay"]),
    )
    total_steps = max(1, len(train_loader) * int(training["max_epochs"]))
    warmup_steps = int(round(total_steps * float(training["warmup_ratio"])))
    scheduler = get_linear_schedule_with_warmup(optimizer, warmup_steps, total_steps)
    mixed_precision = bool(training["mixed_precision"]) and device.type == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=mixed_precision)
    history: list[dict[str, object]] = []
    sampled_rows: list[dict[str, object]] = []
    best_metric = -float("inf")
    best_epoch = 0
    stale_epochs = 0

    for epoch in range(1, int(training["max_epochs"]) + 1):
        started = time.perf_counter()
        model.train()
        losses = []
        sampled = Counter()
        for batch in train_loader:
            indices = batch.pop("example_index")
            for index in indices:
                row = train.iloc[int(index)]
                sampled[(str(row["target"]), str(row["label"]))] += 1
            inputs = {key: value.to(device) for key, value in batch.items()}
            optimizer.zero_grad(set_to_none=True)
            with torch.amp.autocast(device_type=device.type, enabled=mixed_precision):
                output = model(**inputs)
                loss = output.loss
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), float(training["gradient_clip_norm"]))
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()
            losses.append(float(loss.detach().cpu()))
        validation_loss, _, metrics = _validation_pass(
            model, validation_loader, validation, labels, device,
        )
        primary = float(metrics["mean_per_target_macro_f1"])
        improved = primary > best_metric + 1e-12
        if improved:
            best_metric = primary
            best_epoch = epoch
            stale_epochs = 0
            checkpoint_dir.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(checkpoint_dir, safe_serialization=True)
            tokenizer.save_pretrained(checkpoint_dir)
            save_checkpoint_support_files(
                checkpoint_dir,
                config,
                resolved_revision,
                {"best_epoch": best_epoch, "best_validation_primary_metric": best_metric},
            )
        else:
            stale_epochs += 1
        history.append({
            "epoch": epoch,
            "train_loss": float(np.mean(losses)) if losses else float("nan"),
            "validation_loss": validation_loss,
            "validation_primary_metric": primary,
            "validation_global_macro_f1": metrics["macro_f1"],
            "validation_weighted_f1": metrics["weighted_f1"],
            "validation_accuracy": metrics["accuracy"],
            "learning_rate": scheduler.get_last_lr()[0],
            "epoch_duration_seconds": time.perf_counter() - started,
            "best_checkpoint": improved,
        })
        for (target, label), count in sorted(sampled.items()):
            sampled_rows.append({"epoch": epoch, "target": target, "label": label, "sampled_examples": count})
        if stale_epochs >= int(training["early_stopping_patience"]):
            break

    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    best_model = AutoModelForSequenceClassification.from_pretrained(checkpoint_dir).to(device)
    best_tokenizer = AutoTokenizer.from_pretrained(checkpoint_dir, use_fast=True)
    return {
        "model": best_model,
        "tokenizer": best_tokenizer,
        "device": device,
        "hardware": hardware,
        "resolved_revision": resolved_revision,
        "history": pd.DataFrame(history),
        "sampled_distribution": pd.DataFrame(sampled_rows),
        "best_epoch": best_epoch,
        "best_validation_primary_metric": best_metric,
    }
