"""Version 3 orchestration, comparison and persistence."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from ..constants import TARGETS
from ..evaluation import build_error_analysis, evaluate_gold
from ..pipeline import (
    _plot_gold_metrics,
    _plot_status,
    _portable_path,
    _sha256,
    _validate_input,
    coverage_by_language_target,
    language_summary,
    validate_supervision,
)
from .constants import OUTPUT_VERSION, POLICY_VERSION
from .evaluation import audit_supervision_v3, detector_summary, exact_template_consistency
from .extraction import V3ReportLabelExtractor, report_sha256
from .reporting import write_v3_implementation_report, write_v3_stage_report


ARTIFACT_FILES = {
    "supervision": f"supervision_long_{OUTPUT_VERSION}.csv",
    "metrics": f"gold_metrics_{OUTPUT_VERSION}.csv",
    "errors": f"error_analysis_{OUTPUT_VERSION}.csv",
    "languages": f"language_summary_{OUTPUT_VERSION}.csv",
    "coverage": f"coverage_by_language_target_{OUTPUT_VERSION}.csv",
    "coverage_delta": f"coverage_delta_v2_{OUTPUT_VERSION}.csv",
    "transitions": f"status_transitions_v2_{OUTPUT_VERSION}.csv",
    "newly_resolved": f"newly_resolved_pairs_v2_{OUTPUT_VERSION}.csv",
    "detectors": f"detector_summary_{OUTPUT_VERSION}.csv",
    "templates": f"template_consistency_{OUTPUT_VERSION}.csv",
    "audit_summary": f"consistency_audit_summary_{OUTPUT_VERSION}.csv",
    "audit_issues": f"consistency_audit_issues_{OUTPUT_VERSION}.csv",
    "metadata": f"run_metadata_{OUTPUT_VERSION}.json",
}
FIGURE_FILES = {
    "status": f"status_coverage_by_target_{OUTPUT_VERSION}.png",
    "metrics": f"gold_metrics_by_target_{OUTPUT_VERSION}.png",
    "delta": f"resolved_coverage_delta_v2_{OUTPUT_VERSION}.png",
}


def build_supervision_v3(train: pd.DataFrame, extractor: V3ReportLabelExtractor | None = None) -> pd.DataFrame:
    extractor = extractor or V3ReportLabelExtractor()
    rows: list[dict[str, object]] = []
    for record in train.to_dict("records"):
        uid, report = str(record["StudyInstanceUID"]), record["Report"]
        extracted = extractor.extract(report)
        for target in TARGETS:
            result = extracted[target]
            official = None if pd.isna(record[target]) else int(record[target])
            final = official if official is not None else result.derived_label
            source = "official" if official is not None else ("report_derived" if result.derived_label is not None else "unresolved")
            rows.append({
                "StudyInstanceUID": uid,
                "report_sha256": report_sha256(report),
                "language_group": extractor.language_group(report),
                "target": target,
                "status": result.status,
                "derived_label": result.derived_label,
                "derived_score": result.derived_score,
                "confidence": result.confidence,
                "evidence": json.dumps(result.evidence, ensure_ascii=False),
                "rationale": result.rationale,
                "phenotypes": json.dumps(result.phenotypes, ensure_ascii=False),
                "detectors": json.dumps(result.detectors, ensure_ascii=False),
                "evidence_provenance": json.dumps(result.evidence_provenance, ensure_ascii=False),
                "official_label": official,
                "final_label": final,
                "final_source": source,
                "policy_version": POLICY_VERSION,
            })
    frame = pd.DataFrame(rows)
    for column in ("derived_label", "official_label", "final_label"):
        frame[column] = frame[column].astype("Int64")
    return frame


def _compare_v2(v2: pd.DataFrame, v3: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    keys = ["StudyInstanceUID", "target"]
    joined = v2[keys + ["language_group", "status"]].merge(
        v3[keys + ["status"]], on=keys, suffixes=("_v2", "_v3"), validate="one_to_one",
    )
    transitions = joined.groupby(["language_group", "target", "status_v2", "status_v3"]).size().rename("pairs").reset_index()
    rows = []
    for dimensions in (("target",), ("language_group",), ("language_group", "target")):
        grouped = joined.groupby(list(dimensions), dropna=False)
        for key, part in grouped:
            values = key if isinstance(key, tuple) else (key,)
            record = {"scope": "+".join(dimensions), "language_group": None, "target": None}
            record.update(dict(zip(dimensions, values)))
            v2_rate = part["status_v2"].isin(["positive", "negative"]).mean()
            v3_rate = part["status_v3"].isin(["positive", "negative"]).mean()
            record.update({"pairs": len(part), "resolved_rate_v2": v2_rate, "resolved_rate_v3": v3_rate, "delta": v3_rate - v2_rate})
            rows.append(record)
    details = v2[keys + ["status"]].merge(
        v3[[
            *keys, "language_group", "status", "derived_label", "confidence", "evidence",
            "phenotypes", "detectors", "evidence_provenance",
        ]],
        on=keys, suffixes=("_v2", "_v3"), validate="one_to_one",
    )
    newly_resolved = details[
        details["status_v2"].eq("unknown")
        & details["status_v3"].isin(["positive", "negative"])
    ].sort_values(["language_group", "target", "StudyInstanceUID"])
    return pd.DataFrame(rows), transitions, newly_resolved


def _plot_delta(delta: pd.DataFrame, path: Path) -> None:
    target = delta[delta["scope"].eq("target")].set_index("target").reindex(TARGETS)
    fig, ax = plt.subplots(figsize=(11, 5.5))
    colors = ["#2a9d8f" if value >= 0 else "#e76f51" for value in target["delta"]]
    ax.bar(target.index, target["delta"] * 100, color=colors)
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set_ylabel("Resolved coverage delta (percentage points)")
    ax.set_title("V3 minus v2 binary coverage by target")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def run_pipeline_v3(
    train_path: Path,
    artifact_dir: Path,
    figure_dir: Path,
    stage_report_path: Path,
    implementation_report_path: Path,
    expected_studies: int = 4407,
    expected_gold: int = 58,
    config_path: Path | None = None,
    v2_supervision_path: Path | None = None,
) -> dict[str, Path]:
    train_path = train_path.resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)
    stage_report_path.parent.mkdir(parents=True, exist_ok=True)
    implementation_report_path.parent.mkdir(parents=True, exist_ok=True)
    train = pd.read_csv(train_path, dtype={"StudyInstanceUID": str})
    _validate_input(train, expected_studies, expected_gold)

    # Extraction and all corpus-only checks happen before the fixed gold is evaluated.
    supervision = build_supervision_v3(train)
    validate_supervision(supervision, train, expected_studies)
    coverage = coverage_by_language_target(supervision)
    languages = language_summary(train, supervision)
    audit_summary, audit_issues = audit_supervision_v3(supervision, train)
    templates = exact_template_consistency(train, supervision)
    detectors = detector_summary(supervision)
    inconsistent_templates = int(templates["inconsistent_targets"].sum())
    if not audit_issues.empty or inconsistent_templates != 0:
        audit_counts = audit_issues["check"].value_counts().to_dict()
        raise ValueError(
            "v3 corpus-only consistency validation failed: "
            f"audit={audit_counts}, inconsistent_template_targets={inconsistent_templates}"
        )

    v2_path = (v2_supervision_path or artifact_dir / "supervision_long_v2.csv").resolve()
    v2 = pd.read_csv(v2_path, dtype={"StudyInstanceUID": str})
    coverage_delta, transitions, newly_resolved = _compare_v2(v2, supervision)

    # The 58-study gold is a final frozen sentinel, never a rule-discovery input.
    metrics = evaluate_gold(supervision)
    errors = build_error_analysis(supervision, train).merge(
        supervision[["StudyInstanceUID", "target", "phenotypes", "detectors", "evidence_provenance"]],
        on=["StudyInstanceUID", "target"], how="left", validate="one_to_one",
    )

    paths = {key: artifact_dir / name for key, name in ARTIFACT_FILES.items()}
    figures = {key: figure_dir / name for key, name in FIGURE_FILES.items()}
    frames = {
        "supervision": supervision, "metrics": metrics, "errors": errors,
        "languages": languages, "coverage": coverage, "coverage_delta": coverage_delta,
        "transitions": transitions, "newly_resolved": newly_resolved,
        "detectors": detectors, "templates": templates,
        "audit_summary": audit_summary, "audit_issues": audit_issues,
    }
    for key, frame in frames.items():
        frame.to_csv(paths[key], index=False, lineterminator="\n")
    _plot_status(supervision, figures["status"])
    _plot_gold_metrics(metrics, figures["metrics"])
    _plot_delta(coverage_delta, figures["delta"])

    configuration = None
    if config_path is not None:
        resolved = config_path.resolve()
        configuration = {"path": _portable_path(resolved), "sha256": _sha256(resolved)}
    metadata = {
        "stage": "03_report_label_generation",
        "policy_version": POLICY_VERSION,
        "execution_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "input": {"path": _portable_path(train_path), "sha256": _sha256(train_path)},
        "v2_baseline": {"path": _portable_path(v2_path), "sha256": _sha256(v2_path)},
        "configuration": configuration,
        "counts": {
            "studies": expected_studies, "targets": len(TARGETS), "study_target_rows": len(supervision),
            "gold_studies": expected_gold, "gold_study_target_rows": int(supervision["official_label"].notna().sum()),
            "binary_resolved": int(supervision["derived_label"].notna().sum()),
            "unknown": int(supervision["status"].eq("unknown").sum()),
        },
        "policy_guarantees": {
            "missing_mention": "unknown",
            "gold_role": "single final frozen sentinel; excluded from rule discovery and corpus-only validation",
            "ensemble_unit": "mention/proposition evidence, not label voting",
            "confidence": "deterministic evidence-strength rank; not a calibrated probability",
        },
        "schema": {column: str(dtype) for column, dtype in supervision.dtypes.items()},
        "artifacts": {key: {"path": _portable_path(path), "sha256": _sha256(path)} for key, path in paths.items() if key != "metadata"},
        "figures": {key: {"path": _portable_path(path), "sha256": _sha256(path)} for key, path in figures.items()},
        "reproducibility": "Semantic artifacts are deterministic for fixed input/code; execution_timestamp_utc changes per run.",
    }
    paths["metadata"].write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_v3_stage_report(stage_report_path, train, supervision, metrics, errors, languages, coverage_delta, transitions, detectors, templates, audit_summary, paths, figures)
    write_v3_implementation_report(implementation_report_path, paths, figures)
    return {**paths, **{f"figure_{key}": value for key, value in figures.items()}, "stage_report": stage_report_path, "implementation_report": implementation_report_path}
