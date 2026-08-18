"""Hugging Face sentence-pair model construction and inference."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Sequence

import pandas as pd


def ordered_labels(label2id: Mapping[str, int]) -> list[str]:
    ids = sorted(int(value) for value in label2id.values())
    if ids != list(range(len(ids))):
        raise ValueError("label IDs must be contiguous from zero")
    by_id = {int(value): str(label) for label, value in label2id.items()}
    return [by_id[index] for index in ids]


def model_pair(row: Mapping[str, object]) -> tuple[str, str]:
    """Return the only two text fields supplied to the Transformer."""
    return str(row["target_description"]), str(row["raw_clause"])


class PairDataset:
    """Minimal torch-compatible dataset with on-demand pair tokenization."""

    def __init__(
        self,
        frame: pd.DataFrame,
        tokenizer: object,
        label2id: Mapping[str, int],
        max_length: int,
        include_labels: bool = True,
    ) -> None:
        self.frame = frame.reset_index(drop=True)
        self.tokenizer = tokenizer
        self.label2id = {str(key): int(value) for key, value in label2id.items()}
        self.max_length = int(max_length)
        self.include_labels = include_labels

    def __len__(self) -> int:
        return len(self.frame)

    def __getitem__(self, index: int) -> dict[str, object]:
        row = self.frame.iloc[index]
        text, text_pair = model_pair(row)
        encoded = self.tokenizer(
            text,
            text_pair,
            truncation=True,
            max_length=self.max_length,
            padding=False,
        )
        if self.include_labels:
            encoded["labels"] = self.label2id[str(row["label"])]
        encoded["example_index"] = int(index)
        return encoded


class PairCollator:
    """Dynamically pad pair encodings while retaining local row indices."""

    def __init__(self, tokenizer: object) -> None:
        self.tokenizer = tokenizer

    def __call__(self, features: list[dict[str, object]]) -> dict[str, object]:
        indices = [int(feature.pop("example_index")) for feature in features]
        batch = self.tokenizer.pad(features, padding=True, return_tensors="pt")
        batch["example_index"] = indices
        return batch


def load_tokenizer_and_model(config: Mapping[str, object]) -> tuple[object, object, str | None]:
    """Load an AutoModel-compatible encoder with explicit label semantics."""
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    model_config = config["model"]
    label2id = {str(key): int(value) for key, value in config["labels"]["label2id"].items()}
    id2label = {value: key for key, value in label2id.items()}
    model_name = str(model_config["name_or_path"])
    tokenizer_name = str(model_config.get("tokenizer_name_or_path", model_name))
    revision = model_config.get("revision") or None
    local_files_only = bool(model_config.get("local_files_only", False))
    tokenizer = AutoTokenizer.from_pretrained(
        tokenizer_name, revision=revision, use_fast=True, local_files_only=local_files_only,
    )
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        revision=revision,
        num_labels=len(label2id),
        label2id=label2id,
        id2label=id2label,
        local_files_only=local_files_only,
    )
    resolved = getattr(model.config, "_commit_hash", None) or getattr(tokenizer, "init_kwargs", {}).get("_commit_hash")
    return tokenizer, model, resolved


def save_checkpoint_support_files(
    checkpoint_dir: Path,
    config: Mapping[str, object],
    resolved_revision: str | None,
    training_summary: Mapping[str, object],
) -> None:
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    (checkpoint_dir / "stage04_config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8",
    )
    metadata = {
        "checkpoint_definition": "Persisted model, tokenizer and configuration required to reconstruct inference without retraining.",
        "model_identifier": config["model"]["name_or_path"],
        "configured_revision": config["model"].get("revision"),
        "resolved_revision": resolved_revision,
        "target_descriptions": config["targets"],
        "label2id": config["labels"]["label2id"],
        "upstream_policy_version": config["upstream_policy_version"],
        "training_summary": dict(training_summary),
    }
    (checkpoint_dir / "checkpoint_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8",
    )


def count_truncated_examples(
    tokenizer: object,
    frame: pd.DataFrame,
    max_length: int,
) -> tuple[int, int]:
    truncated = 0
    maximum = 0
    for row in frame.to_dict("records"):
        text, text_pair = model_pair(row)
        length = len(tokenizer(text, text_pair, truncation=False, padding=False)["input_ids"])
        maximum = max(maximum, length)
        truncated += int(length > max_length)
    return truncated, maximum


def predict_frame(
    model: object,
    tokenizer: object,
    frame: pd.DataFrame,
    label2id: Mapping[str, int],
    max_length: int,
    batch_size: int,
    device: object,
) -> pd.DataFrame:
    """Return logits and explicitly uncalibrated softmax scores."""
    import torch
    from torch.utils.data import DataLoader

    labels = ordered_labels(label2id)
    dataset = PairDataset(frame, tokenizer, label2id, max_length, include_labels="label" in frame)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, collate_fn=PairCollator(tokenizer))
    prediction_ids: list[int] = []
    logits_rows: list[list[float]] = []
    model.eval()
    with torch.no_grad():
        for batch in loader:
            indices = batch.pop("example_index")
            batch.pop("labels", None)
            inputs = {key: value.to(device) for key, value in batch.items()}
            logits = model(**inputs).logits.detach().cpu()
            prediction_ids.extend(logits.argmax(dim=-1).tolist())
            logits_rows.extend(logits.tolist())
    logits_tensor = torch.tensor(logits_rows, dtype=torch.float32)
    scores = torch.softmax(logits_tensor, dim=-1).tolist() if logits_rows else []
    output = frame.reset_index(drop=True).copy()
    output["predicted_label"] = [labels[index] for index in prediction_ids]
    for index, label in enumerate(labels):
        output[f"logit_{label}"] = [row[index] for row in logits_rows]
        output[f"softmax_score_{label}"] = [row[index] for row in scores]
    return output
