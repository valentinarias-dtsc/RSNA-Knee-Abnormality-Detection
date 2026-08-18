"""Deterministic clause-to-Study aggregation kept separate from the encoder."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


AGGREGATION_PRECEDENCE = ("positive", "uncertain", "negative")


def aggregate_labels(labels: Iterable[str]) -> str:
    observed = set(labels)
    for label in AGGREGATION_PRECEDENCE:
        if label in observed:
            return label
    return "unknown"


def aggregate_clause_predictions(predictions: pd.DataFrame) -> pd.DataFrame:
    """Aggregate local predictions using positive > uncertain > negative."""
    required = {"StudyInstanceUID", "target", "predicted_label"}
    if missing := required - set(predictions.columns):
        raise ValueError(f"predictions missing columns: {sorted(missing)}")
    rows: list[dict[str, object]] = []
    for (uid, target), part in predictions.groupby(["StudyInstanceUID", "target"], sort=True):
        nonempty = part[~part["predicted_label"].eq("no_evidence")]
        rows.append({
            "StudyInstanceUID": uid,
            "target": target,
            "predicted_status": aggregate_labels(part["predicted_label"]),
            "strict_clause_count": part["source_index"].nunique() if "source_index" in part else len(part),
            "evidence_clause_count": len(nonempty),
            "positive_clause_count": int(part["predicted_label"].eq("positive").sum()),
            "uncertain_clause_count": int(part["predicted_label"].eq("uncertain").sum()),
            "negative_clause_count": int(part["predicted_label"].eq("negative").sum()),
            "no_evidence_clause_count": int(part["predicted_label"].eq("no_evidence").sum()),
        })
    return pd.DataFrame(rows)


def study_level_weak_agreement(
    aggregated: pd.DataFrame,
    derived_statuses: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Compare aggregation only with v3 derived status, never official/final labels."""
    teacher = derived_statuses[["StudyInstanceUID", "target", "status"]].rename(
        columns={"status": "teacher_derived_status"}
    )
    joined = aggregated.merge(teacher, on=["StudyInstanceUID", "target"], validate="one_to_one")
    joined["agreement"] = joined["predicted_status"].eq(joined["teacher_derived_status"])
    joined["teacher_resolved"] = ~joined["teacher_derived_status"].eq("unknown")
    transitions = joined.groupby(
        ["target", "teacher_derived_status", "predicted_status"], dropna=False,
    ).size().rename("count").reset_index()
    rows = [{
        "target": "__all__",
        "pairs": len(joined),
        "agreement": float(joined["agreement"].mean()) if len(joined) else float("nan"),
        "coverage": float((~joined["predicted_status"].eq("unknown")).mean()) if len(joined) else float("nan"),
        "teacher_resolved_pairs": int(joined["teacher_resolved"].sum()),
    }]
    for target, part in joined.groupby("target", sort=True):
        rows.append({
            "target": target,
            "pairs": len(part),
            "agreement": float(part["agreement"].mean()),
            "coverage": float((~part["predicted_status"].eq("unknown")).mean()),
            "teacher_resolved_pairs": int(part["teacher_resolved"].sum()),
        })
    return joined, transitions, pd.DataFrame(rows)
