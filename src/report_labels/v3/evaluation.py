"""Corpus-only validation and exhaustive persistence audit for v3."""

from __future__ import annotations

import json
import re

import pandas as pd

from ..constants import TARGETS
from ..text import normalize_text
from .constants import POLICY_VERSION
from .text import build_text_views


ISSUE_COLUMNS = [
    "check", "severity", "StudyInstanceUID", "target", "status", "rationale", "detail",
]


def audit_supervision_v3(long_labels: pd.DataFrame, train: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Audit every v3 row, evidence span and structured provenance payload."""
    issues: list[dict[str, object]] = []
    reports = train.assign(StudyInstanceUID=train["StudyInstanceUID"].astype(str)).set_index("StudyInstanceUID")["Report"]
    view_cache: dict[str, set[str]] = {}

    checks = {
        "unique_study_target": len(long_labels),
        "policy_version": len(long_labels),
        "status_value_schema": len(long_labels),
        "missing_mention_unknown": int(long_labels["status"].eq("unknown").sum()),
        "binary_status_mapping": int(long_labels["status"].isin(["positive", "negative"]).sum()),
        "uncertain_is_unresolved": int(long_labels["status"].eq("uncertain").sum()),
        "evidence_json_schema": len(long_labels),
        "provenance_json_schema": len(long_labels),
        "evidence_in_diagnostic_view": int(long_labels["status"].ne("unknown").sum()),
        "winning_status_in_provenance": int(long_labels["status"].ne("unknown").sum()),
        "phenotype_detector_alignment": int(long_labels["status"].ne("unknown").sum()),
        "final_provenance_schema": len(long_labels),
    }

    def add(check: str, row: object, detail: str) -> None:
        issues.append({
            "check": check,
            "severity": "error",
            "StudyInstanceUID": str(row.StudyInstanceUID),
            "target": str(row.target),
            "status": str(row.status),
            "rationale": str(row.rationale),
            "detail": detail[:1000],
        })

    duplicated = long_labels.duplicated(["StudyInstanceUID", "target"], keep=False)
    for row in long_labels[duplicated].itertuples(index=False):
        add("unique_study_target", row, "duplicate study-target row")

    for row in long_labels.itertuples(index=False):
        if row.policy_version != POLICY_VERSION:
            add("policy_version", row, f"unexpected policy {row.policy_version}")
        if row.status not in {"positive", "negative", "uncertain", "unknown"}:
            add("status_value_schema", row, f"invalid status {row.status}")

        try:
            evidence = json.loads(row.evidence)
        except (TypeError, json.JSONDecodeError) as exc:
            evidence = []
            add("evidence_json_schema", row, repr(exc))
        if not isinstance(evidence, list) or not all(isinstance(value, str) for value in evidence):
            add("evidence_json_schema", row, "evidence must be a JSON string list")
            evidence = []

        try:
            provenance = json.loads(row.evidence_provenance)
            phenotypes = json.loads(row.phenotypes)
            detectors = json.loads(row.detectors)
        except (TypeError, json.JSONDecodeError) as exc:
            provenance, phenotypes, detectors = [], [], []
            add("provenance_json_schema", row, repr(exc))
        if not isinstance(provenance, list) or not all(isinstance(value, dict) for value in provenance):
            add("provenance_json_schema", row, "provenance must be a JSON object list")
            provenance = []

        if row.status == "unknown":
            if pd.notna(row.derived_label) or evidence or provenance or phenotypes or detectors or row.confidence != 0:
                add("missing_mention_unknown", row, "unknown row contains a derived value or evidence")
        elif row.status == "uncertain":
            if pd.notna(row.derived_label):
                add("uncertain_is_unresolved", row, "uncertain was binarized")
        else:
            expected = 1 if row.status == "positive" else 0
            if pd.isna(row.derived_label) or int(row.derived_label) != expected:
                add("binary_status_mapping", row, f"expected label {expected}")

        if row.status != "unknown":
            if not evidence or not provenance:
                add("provenance_json_schema", row, "resolved/uncertain row lacks evidence or provenance")
            uid = str(row.StudyInstanceUID)
            if uid not in view_cache:
                view_cache[uid] = {view.text for view in build_text_views(reports.loc[uid]) if view.diagnostic}
            for item in evidence:
                if item not in view_cache[uid]:
                    add("evidence_in_diagnostic_view", row, f"evidence not found in a diagnostic v3 view: {item}")
            if not any(item.get("status") == row.status for item in provenance):
                add("winning_status_in_provenance", row, "winning status absent from provenance")
            provenance_evidence = {item.get("evidence") for item in provenance}
            if not set(evidence).issubset(provenance_evidence):
                add("provenance_json_schema", row, "persisted evidence is not represented in provenance")
            provenance_phenotypes = {item.get("phenotype") for item in provenance}
            provenance_detectors = {detector for item in provenance for detector in item.get("detectors", [])}
            if not set(phenotypes).issubset(provenance_phenotypes) or not set(detectors).issubset(provenance_detectors):
                add("phenotype_detector_alignment", row, "summary fields disagree with provenance")

        if row.official_label is not None and pd.notna(row.official_label):
            if int(row.final_label) != int(row.official_label) or row.final_source != "official":
                add("final_provenance_schema", row, "official override/provenance mismatch")
        elif pd.notna(row.derived_label):
            if int(row.final_label) != int(row.derived_label) or row.final_source != "report_derived":
                add("final_provenance_schema", row, "derived final/provenance mismatch")
        elif pd.notna(row.final_label) or row.final_source != "unresolved":
            add("final_provenance_schema", row, "unresolved row received a final label")

    issue_frame = pd.DataFrame(issues, columns=ISSUE_COLUMNS)
    rows = []
    for check, evaluated in checks.items():
        count = int((issue_frame["check"] == check).sum()) if not issue_frame.empty else 0
        rows.append({
            "check": check,
            "severity": "error",
            "evaluated_rows": int(evaluated),
            "issue_count": count,
            "passed": count == 0,
        })
    return pd.DataFrame(rows), issue_frame


def exact_template_consistency(train: pd.DataFrame, supervision: pd.DataFrame) -> pd.DataFrame:
    """Validate exact and numeric-normalized corpus template families."""
    base = train[["StudyInstanceUID", "Report"]].copy()
    base["StudyInstanceUID"] = base["StudyInstanceUID"].astype(str)
    base["exact"] = base["Report"].map(normalize_text)
    base["numeric_normalized"] = base["exact"].map(
        lambda value: re.sub(r"\b\d+(?:[.,]\d+)*\b", "<num>", value)
    )
    outputs: list[pd.DataFrame] = []
    for mode in ("exact", "numeric_normalized"):
        counts = base[mode].value_counts()
        duplicates = base[base[mode].isin(counts[counts > 1].index)].copy()
        if duplicates.empty:
            continue
        duplicates["template_sha256"] = duplicates[mode].map(
            lambda value: __import__("hashlib").sha256(f"{mode}:{value}".encode("utf-8")).hexdigest()
        )
        joined = duplicates[["StudyInstanceUID", "template_sha256"]].merge(
            supervision[["StudyInstanceUID", "target", "status", "derived_label"]],
            on="StudyInstanceUID", validate="one_to_many",
        )
        inconsistency = joined.groupby(["template_sha256", "target"], sort=False).agg(
            status_values=("status", "nunique"),
            label_values=("derived_label", lambda values: values.astype("string").nunique()),
        ).reset_index()
        bad = inconsistency[(inconsistency["status_values"] > 1) | (inconsistency["label_values"] > 1)]
        studies = duplicates.groupby("template_sha256").size().rename("studies")
        bad_counts = bad.groupby("template_sha256").size().rename("inconsistent_targets")
        output = studies.to_frame().join(bad_counts, how="left").fillna({"inconsistent_targets": 0}).reset_index()
        output.insert(0, "template_mode", mode)
        outputs.append(output)
    if not outputs:
        return pd.DataFrame(columns=["template_mode", "template_sha256", "studies", "inconsistent_targets"])
    return pd.concat(outputs, ignore_index=True)


def detector_summary(supervision: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for row in supervision[supervision["status"].ne("unknown")].itertuples(index=False):
        for item in json.loads(row.evidence_provenance):
            for detector in item.get("detectors", []):
                rows.append({
                    "language_group": row.language_group,
                    "target": row.target,
                    "status": item.get("status"),
                    "phenotype": item.get("phenotype"),
                    "detector": detector,
                    "view": ",".join(item.get("views", [])),
                })
    if not rows:
        return pd.DataFrame(columns=["language_group", "target", "status", "phenotype", "detector", "view", "propositions"])
    return pd.DataFrame(rows).groupby(
        ["language_group", "target", "status", "phenotype", "detector", "view"], dropna=False,
    ).size().rename("propositions").reset_index().sort_values("propositions", ascending=False)
