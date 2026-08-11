"""Stage 03 orchestration: extraction, evaluation, override and persistence."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .constants import POLICY_VERSION, TARGETS, VALID_FINAL_SOURCES, VALID_STATUSES
from .evaluation import build_error_analysis, evaluate_gold
from .extraction import ReportLabelExtractor, report_sha256
from .reporting import write_implementation_report, write_stage_report


ARTIFACT_FILES = {
    "supervision": "supervision_long_v1.csv",
    "metrics": "gold_metrics_v1.csv",
    "errors": "error_analysis_v1.csv",
    "languages": "language_summary_v1.csv",
    "metadata": "run_metadata_v1.json",
}
FIGURE_FILES = {
    "status": "status_coverage_by_target_v1.png",
    "metrics": "gold_metrics_by_target_v1.png",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _portable_path(path: Path) -> str:
    repo_root = Path(__file__).resolve().parents[2]
    try:
        return path.resolve().relative_to(repo_root).as_posix()
    except ValueError:
        return str(path.resolve())


def _validate_input(train: pd.DataFrame, expected_studies: int, expected_gold: int) -> None:
    required = {"StudyInstanceUID", "Report", *TARGETS}
    missing = required.difference(train.columns)
    if missing:
        raise ValueError(f"train.csv missing required columns: {sorted(missing)}")
    if len(train) != expected_studies or train["StudyInstanceUID"].nunique() != expected_studies:
        raise ValueError(f"expected {expected_studies} unique studies, found {len(train)} rows and {train['StudyInstanceUID'].nunique()} IDs")
    if train["StudyInstanceUID"].duplicated().any():
        raise ValueError("duplicate StudyInstanceUID in train.csv")
    if train["Report"].isna().any():
        raise ValueError("Report contains missing values")
    observed = train[list(TARGETS)].notna()
    partial = observed.any(axis=1) & ~observed.all(axis=1)
    if partial.any():
        raise ValueError("partially observed official target rows are unsupported")
    if int(observed.all(axis=1).sum()) != expected_gold:
        raise ValueError(f"expected {expected_gold} complete gold studies")
    values = set(pd.unique(train[list(TARGETS)].stack()))
    if not values.issubset({0.0, 1.0}):
        raise ValueError(f"official labels outside binary domain: {values}")


def build_supervision(train: pd.DataFrame, extractor: ReportLabelExtractor | None = None) -> pd.DataFrame:
    extractor = extractor or ReportLabelExtractor()
    rows: list[dict[str, object]] = []
    for record in train.to_dict("records"):
        uid = str(record["StudyInstanceUID"])
        report = record["Report"]
        group = extractor.language_group(report)
        digest = report_sha256(report)
        extracted = extractor.extract(report)
        for target in TARGETS:
            result = extracted[target]
            official = record[target]
            official_value = None if pd.isna(official) else int(official)
            final_label = official_value if official_value is not None else result.derived_label
            final_source = "official" if official_value is not None else ("report_derived" if result.derived_label is not None else "unresolved")
            rows.append({
                "StudyInstanceUID": uid,
                "report_sha256": digest,
                "language_group": group,
                "target": target,
                "status": result.status,
                "derived_label": result.derived_label,
                "derived_score": result.derived_score,
                "confidence": result.confidence,
                "evidence": json.dumps(result.evidence, ensure_ascii=False),
                "rationale": result.rationale,
                "official_label": official_value,
                "final_label": final_label,
                "final_source": final_source,
                "policy_version": POLICY_VERSION,
            })
    frame = pd.DataFrame(rows)
    for column in ("derived_label", "official_label", "final_label"):
        frame[column] = frame[column].astype("Int64")
    return frame


def validate_supervision(frame: pd.DataFrame, train: pd.DataFrame, expected_studies: int) -> None:
    expected_rows = expected_studies * len(TARGETS)
    if len(frame) != expected_rows or frame[["StudyInstanceUID", "target"]].duplicated().any():
        raise ValueError("supervision must have exactly one row per study-target pair")
    if set(frame["StudyInstanceUID"]) != set(train["StudyInstanceUID"].astype(str)):
        raise ValueError("supervision lost or introduced StudyInstanceUID values")
    if set(frame["target"]) != set(TARGETS):
        raise ValueError("supervision target domain mismatch")
    if not set(frame["status"]).issubset(VALID_STATUSES):
        raise ValueError("invalid extraction status")
    if not set(frame["final_source"]).issubset(VALID_FINAL_SOURCES):
        raise ValueError("invalid final provenance")
    if not frame["confidence"].between(0, 1).all():
        raise ValueError("confidence outside [0, 1]")
    resolved = frame["derived_label"].dropna()
    if not set(resolved.astype(int)).issubset({0, 1}):
        raise ValueError("derived labels outside binary domain")
    gold = frame[frame["official_label"].notna()]
    if not gold["final_label"].equals(gold["official_label"]):
        raise ValueError("gold override failed")
    if not gold["final_source"].eq("official").all():
        raise ValueError("gold provenance failed")
    unresolved = frame[frame["status"].isin(["unknown", "uncertain"]) & frame["official_label"].isna()]
    if unresolved["final_label"].notna().any():
        raise ValueError("unknown/uncertain weak labels were silently resolved")


def language_summary(train: pd.DataFrame, supervision: pd.DataFrame) -> pd.DataFrame:
    studies = supervision[["StudyInstanceUID", "language_group"]].drop_duplicates()
    base = train[["StudyInstanceUID", "Report"]].copy()
    base["StudyInstanceUID"] = base["StudyInstanceUID"].astype(str)
    base["gold_study"] = train[list(TARGETS)].notna().all(axis=1).to_numpy()
    base["report_chars"] = base["Report"].str.len()
    base = base.merge(studies, on="StudyInstanceUID", how="left", validate="one_to_one")
    summary = base.groupby("language_group", sort=True).agg(
        studies=("StudyInstanceUID", "size"),
        gold_studies=("gold_study", "sum"),
        mean_report_chars=("report_chars", "mean"),
    ).reset_index()
    statuses = supervision.groupby(["language_group", "status"]).size().unstack(fill_value=0)
    for status in VALID_STATUSES:
        if status not in statuses:
            statuses[status] = 0
    summary = summary.merge(statuses[list(VALID_STATUSES)].reset_index(), on="language_group", how="left")
    summary["resolved_rate"] = (summary["positive"] + summary["negative"]) / (summary["studies"] * len(TARGETS))
    return summary


def _plot_status(supervision: pd.DataFrame, path: Path) -> None:
    table = supervision.groupby(["target", "status"]).size().unstack(fill_value=0).reindex(TARGETS)
    colors = {"positive": "#b2182b", "negative": "#2166ac", "uncertain": "#fdae61", "unknown": "#bdbdbd"}
    fig, ax = plt.subplots(figsize=(12, 6.5))
    bottom = np.zeros(len(table))
    for status in VALID_STATUSES:
        values = table.get(status, pd.Series(0, index=table.index)).to_numpy()
        ax.bar(table.index, values, bottom=bottom, label=status, color=colors[status])
        bottom += values
    ax.set_ylabel("Study-target states")
    ax.set_title("Report extraction states across 4,407 studies")
    ax.tick_params(axis="x", rotation=45)
    ax.legend(ncol=4, frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _plot_gold_metrics(metrics: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), sharey=True)
    x = np.arange(len(metrics))
    axes[0].bar(x, metrics["coverage"], color="#4c78a8")
    axes[0].set_title("Resolved coverage on gold studies")
    axes[0].set_ylim(0, 1.05)
    width = 0.25
    for offset, column, color in [(-width, "precision", "#59a14f"), (0, "recall", "#e15759"), (width, "f1", "#f28e2b")]:
        axes[1].bar(x + offset, metrics[column], width=width, label=column, color=color)
    axes[1].set_title("Metrics on resolved gold cases")
    axes[1].set_ylim(0, 1.05)
    axes[1].legend(frameon=False)
    for ax in axes:
        ax.set_xticks(x, metrics["target"], rotation=55, ha="right")
        ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def run_pipeline(
    train_path: Path,
    artifact_dir: Path,
    figure_dir: Path,
    stage_report_path: Path,
    implementation_report_path: Path,
    expected_studies: int = 4407,
    expected_gold: int = 58,
    config_path: Path | None = None,
) -> dict[str, Path]:
    train_path = train_path.resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)
    stage_report_path.parent.mkdir(parents=True, exist_ok=True)
    implementation_report_path.parent.mkdir(parents=True, exist_ok=True)

    train = pd.read_csv(train_path, dtype={"StudyInstanceUID": str})
    _validate_input(train, expected_studies, expected_gold)
    supervision = build_supervision(train)
    validate_supervision(supervision, train, expected_studies)
    metrics = evaluate_gold(supervision)
    errors = build_error_analysis(supervision, train)
    languages = language_summary(train, supervision)

    paths = {key: artifact_dir / name for key, name in ARTIFACT_FILES.items()}
    figures = {key: figure_dir / name for key, name in FIGURE_FILES.items()}
    supervision.to_csv(paths["supervision"], index=False, lineterminator="\n")
    metrics.to_csv(paths["metrics"], index=False, lineterminator="\n")
    errors.to_csv(paths["errors"], index=False, lineterminator="\n")
    languages.to_csv(paths["languages"], index=False, lineterminator="\n")
    _plot_status(supervision, figures["status"])
    _plot_gold_metrics(metrics, figures["metrics"])

    configuration = None
    if config_path is not None:
        resolved_config = config_path.resolve()
        configuration = {"path": _portable_path(resolved_config), "sha256": _sha256(resolved_config)}
    metadata = {
        "stage": "03 - report label generation",
        "policy_version": POLICY_VERSION,
        "execution_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "input": {"path": _portable_path(train_path), "sha256": _sha256(train_path)},
        "configuration": configuration,
        "counts": {
            "studies": expected_studies,
            "targets": len(TARGETS),
            "study_target_rows": len(supervision),
            "gold_studies": expected_gold,
            "gold_study_target_rows": int(supervision["official_label"].notna().sum()),
        },
        "confidence_definition": {
            "positive_explicit": 0.90,
            "positive_with_conflict": 0.70,
            "negative_explicit": 0.85,
            "uncertain_explicit": 0.50,
            "unknown": 0.0,
            "interpretation": "deterministic evidence-strength rank; not a calibrated probability",
        },
        "schema": {column: str(dtype) for column, dtype in supervision.dtypes.items()},
        "artifacts": {key: {"path": _portable_path(path), "sha256": _sha256(path)} for key, path in paths.items() if key != "metadata"},
        "figures": {key: {"path": _portable_path(path), "sha256": _sha256(path)} for key, path in figures.items()},
        "reproducibility": "Semantic artifacts are deterministic for fixed input/code; execution_timestamp_utc changes per run.",
    }
    paths["metadata"].write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    write_stage_report(stage_report_path, train, supervision, metrics, errors, languages, paths, figures)
    write_implementation_report(implementation_report_path, paths, figures)
    return {**paths, **{f"figure_{key}": value for key, value in figures.items()}, "stage_report": stage_report_path, "implementation_report": implementation_report_path}
