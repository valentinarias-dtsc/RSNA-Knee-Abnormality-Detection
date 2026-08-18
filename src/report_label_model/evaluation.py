"""Weak-label agreement metrics and auditable evaluation slices."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
)


def metric_bundle(
    true_labels: Iterable[str],
    predicted_labels: Iterable[str],
    labels: list[str],
) -> tuple[dict[str, float | int], pd.DataFrame]:
    truth = list(true_labels)
    predictions = list(predicted_labels)
    if len(truth) != len(predictions):
        raise ValueError("truth and predictions have different lengths")
    precision, recall, f1, support = precision_recall_fscore_support(
        truth, predictions, labels=labels, zero_division=0,
    )
    present = support > 0
    macro = float(np.mean(f1[present])) if present.any() else float("nan")
    weighted = float(np.average(f1, weights=support)) if support.sum() else float("nan")
    overall = {
        "support": len(truth),
        "accuracy": float(accuracy_score(truth, predictions)) if truth else float("nan"),
        "macro_f1": macro,
        "weighted_f1": weighted,
        "labels_with_support": int(present.sum()),
    }
    by_label = pd.DataFrame({
        "label": labels,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "support": support.astype(int),
    })
    return overall, by_label


def mean_per_target_macro_f1(
    truth: Iterable[str],
    predictions: Iterable[str],
    targets: Iterable[str],
    labels: list[str],
) -> float:
    frame = pd.DataFrame({
        "truth": list(truth),
        "prediction": list(predictions),
        "target": list(targets),
    })
    values = []
    for _, part in frame.groupby("target", sort=True):
        overall, _ = metric_bundle(part["truth"], part["prediction"], labels)
        if not np.isnan(overall["macro_f1"]):
            values.append(float(overall["macro_f1"]))
    return float(np.mean(values)) if values else float("nan")


def evaluate_frame(
    predictions: pd.DataFrame,
    labels: list[str],
    evaluation_name: str,
) -> dict[str, pd.DataFrame]:
    """Calculate overall, target, label, language, detector and phenotype tables."""
    required = {"label", "predicted_label", "target"}
    if missing := required - set(predictions.columns):
        raise ValueError(f"prediction frame missing columns: {sorted(missing)}")
    overall, by_label = metric_bundle(predictions["label"], predictions["predicted_label"], labels)
    overall["evaluation"] = evaluation_name
    overall["mean_per_target_macro_f1"] = mean_per_target_macro_f1(
        predictions["label"], predictions["predicted_label"], predictions["target"], labels,
    )
    by_label.insert(0, "evaluation", evaluation_name)
    by_label.insert(1, "target", "__all__")

    def grouped_table(column: str) -> pd.DataFrame:
        rows: list[dict[str, object]] = []
        if column not in predictions:
            return pd.DataFrame()
        for value, part in predictions.groupby(column, dropna=False, sort=True):
            metrics, details = metric_bundle(part["label"], part["predicted_label"], labels)
            rows.append({
                "evaluation": evaluation_name,
                column: value,
                "label": "__all__",
                **metrics,
            })
            for detail in details.to_dict("records"):
                rows.append({
                    "evaluation": evaluation_name,
                    column: value,
                    "label": detail["label"],
                    "support": detail["support"],
                    "precision": detail["precision"],
                    "recall": detail["recall"],
                    "f1": detail["f1"],
                })
        return pd.DataFrame(rows)

    matrix = confusion_matrix(predictions["label"], predictions["predicted_label"], labels=labels)
    confusion = pd.DataFrame(matrix, index=labels, columns=labels).rename_axis(
        index="teacher_label", columns="predicted_label",
    ).reset_index()
    confusion.insert(0, "evaluation", evaluation_name)
    return {
        "overall": pd.DataFrame([overall]),
        "by_label": by_label,
        "by_target": grouped_table("target"),
        "by_language": grouped_table("language_group"),
        "by_detector": grouped_table("detector_combination"),
        "by_phenotype": grouped_table("phenotype"),
        "confusion": confusion,
    }


def evaluate_test_slices(predictions: pd.DataFrame, labels: list[str]) -> dict[str, pd.DataFrame]:
    ordered = predictions.sort_values(
        ["target", "label", "normalized_clause", "StudyInstanceUID", "source_index", "example_id"]
    )
    slices = {
        "TEST-ALL": predictions,
        "TEST-UNIQUE": ordered.drop_duplicates(["target", "label", "normalized_clause"]),
        "TEST-NOVEL": predictions[predictions["novel_exact_target_clause"].astype(bool)],
    }
    collected: dict[str, list[pd.DataFrame]] = {
        "overall": [], "by_label": [], "by_target": [], "by_language": [],
        "by_detector": [], "by_phenotype": [], "confusion": [],
    }
    summary_rows = []
    for name, frame in slices.items():
        result = evaluate_frame(frame, labels, name)
        for key, value in result.items():
            collected[key].append(value)
        summary_rows.append({
            "slice": name,
            "examples": len(frame),
            "studies": frame["StudyInstanceUID"].nunique(),
            "unique_target_normalized_clauses": frame[["target", "normalized_clause"]].drop_duplicates().shape[0],
        })
    output = {
        key: pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()
        for key, frames in collected.items()
    }
    output["summary"] = pd.DataFrame(summary_rows)
    return output
