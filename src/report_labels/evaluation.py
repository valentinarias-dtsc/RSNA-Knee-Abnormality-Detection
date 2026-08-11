"""Gold evaluation and auditable error analysis, before official override."""

from __future__ import annotations

import math
import pandas as pd

from .constants import TARGETS


def evaluate_gold(long_labels: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    gold = long_labels[long_labels["official_label"].notna()].copy()
    for target in TARGETS:
        part = gold[gold["target"] == target]
        resolved = part[part["derived_label"].notna()]
        truth = resolved["official_label"].astype(int)
        pred = resolved["derived_label"].astype(int)
        tp = int(((truth == 1) & (pred == 1)).sum())
        tn = int(((truth == 0) & (pred == 0)).sum())
        fp = int(((truth == 0) & (pred == 1)).sum())
        fn = int(((truth == 1) & (pred == 0)).sum())
        precision = tp / (tp + fp) if tp + fp else math.nan
        recall = tp / (tp + fn) if tp + fn else math.nan
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else math.nan
        rows.append({
            "target": target,
            "gold_n": int(len(part)),
            "gold_positives": int((part["official_label"] == 1).sum()),
            "gold_negatives": int((part["official_label"] == 0).sum()),
            "resolved_n": int(len(resolved)),
            "coverage": len(resolved) / len(part) if len(part) else math.nan,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "tp": tp, "tn": tn, "fp": fp, "fn": fn,
            "unknown": int((part["status"] == "unknown").sum()),
            "uncertain": int((part["status"] == "uncertain").sum()),
        })
    return pd.DataFrame(rows)


def build_error_analysis(long_labels: pd.DataFrame, train: pd.DataFrame) -> pd.DataFrame:
    gold = long_labels[long_labels["official_label"].notna()].copy()
    gold["error_type"] = ""
    resolved = gold["derived_label"].notna()
    gold.loc[resolved & (gold["official_label"] == 0) & (gold["derived_label"] == 1), "error_type"] = "FP"
    gold.loc[resolved & (gold["official_label"] == 1) & (gold["derived_label"] == 0), "error_type"] = "FN"
    gold.loc[gold["status"] == "unknown", "error_type"] = "unknown"
    gold.loc[gold["status"] == "uncertain", "error_type"] = "uncertain"
    errors = gold[gold["error_type"] != ""].copy()
    errors = errors.merge(train[["StudyInstanceUID", "Report"]], on="StudyInstanceUID", how="left", validate="many_to_one")
    columns = [
        "StudyInstanceUID", "target", "Report", "official_label", "derived_label",
        "status", "confidence", "evidence", "rationale", "language_group", "error_type",
    ]
    return errors[columns].sort_values(["target", "error_type", "StudyInstanceUID"])
