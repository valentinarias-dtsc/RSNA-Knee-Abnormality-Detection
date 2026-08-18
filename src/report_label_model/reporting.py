"""Small, sober Stage 04 figures generated from persisted tabular data."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _save(fig: object, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def plot_dataset_dedup(summary: pd.DataFrame, path: Path) -> None:
    lookup = summary.set_index("measure")["value"].to_dict()
    labels = ["Train source", "After collision filter", "After dedup"]
    values = [
        lookup.get("train_source_rows", 0),
        lookup.get("train_rows_after_collision_exclusion", 0),
        lookup.get("train_rows_after_dedup", 0),
    ]
    fig, axis = plt.subplots(figsize=(7.5, 4.5))
    bars = axis.bar(labels, values, color=("#5B7FA3", "#6E9F83", "#C28E5C"))
    axis.set_ylabel("Examples")
    axis.set_title("Stage 04 train cardinality before and after deduplication")
    axis.bar_label(bars, fmt="%.0f")
    _save(fig, path)


def plot_training_curves(history: pd.DataFrame, figure_dir: Path) -> list[Path]:
    outputs = []
    fig, axis = plt.subplots(figsize=(7.5, 4.5))
    axis.plot(history["epoch"], history["train_loss"], marker="o", label="Train")
    axis.plot(history["epoch"], history["validation_loss"], marker="o", label="Validation")
    axis.set_xlabel("Epoch")
    axis.set_ylabel("Cross-entropy loss")
    axis.set_title("Training and validation loss")
    axis.legend()
    outputs.append(figure_dir / "training_validation_loss.png")
    _save(fig, outputs[-1])

    fig, axis = plt.subplots(figsize=(7.5, 4.5))
    axis.plot(history["epoch"], history["validation_primary_metric"], marker="o", color="#5B7FA3")
    axis.set_xlabel("Epoch")
    axis.set_ylabel("Mean per-target macro-F1")
    axis.set_title("Validation weak-label selection metric")
    outputs.append(figure_dir / "validation_primary_metric.png")
    _save(fig, outputs[-1])
    return outputs


def plot_confusion(confusion: pd.DataFrame, labels: Sequence[str], title: str, path: Path) -> None:
    matrix = confusion.set_index("teacher_label").loc[list(labels), list(labels)].to_numpy(dtype=float)
    fig, axis = plt.subplots(figsize=(6.5, 5.5))
    image = axis.imshow(matrix, cmap="Blues")
    axis.set_xticks(range(len(labels)), labels, rotation=35, ha="right")
    axis.set_yticks(range(len(labels)), labels)
    axis.set_xlabel("Predicted label")
    axis.set_ylabel("Teacher label")
    axis.set_title(title)
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            axis.text(column, row, f"{int(matrix[row, column])}", ha="center", va="center")
    fig.colorbar(image, ax=axis, shrink=0.8)
    _save(fig, path)


def plot_target_test_comparison(metrics_by_target: pd.DataFrame, path: Path) -> None:
    overall = metrics_by_target[metrics_by_target["label"].eq("__all__")]
    pivot = overall.pivot(index="target", columns="evaluation", values="macro_f1")
    pivot = pivot.reindex(columns=["TEST-ALL", "TEST-NOVEL"])
    positions = np.arange(len(pivot))
    width = 0.4
    fig, axis = plt.subplots(figsize=(11, 5.5))
    axis.bar(positions - width / 2, pivot["TEST-ALL"], width, label="TEST-ALL", color="#5B7FA3")
    axis.bar(positions + width / 2, pivot["TEST-NOVEL"], width, label="TEST-NOVEL", color="#C28E5C")
    axis.set_xticks(positions, pivot.index, rotation=45, ha="right")
    axis.set_ylabel("Macro-F1 against weak labels")
    axis.set_title("Per-target weak-label agreement: TEST-ALL vs TEST-NOVEL")
    axis.legend()
    _save(fig, path)
