"""Gold evaluation and auditable error analysis, before official override."""

from __future__ import annotations

from functools import lru_cache
import json
import math
import pandas as pd

from .constants import POLICY_VERSION, TARGETS
from .text import segment_report


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


def audit_supervision_consistency(
    long_labels: pd.DataFrame,
    train: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Audit every persisted row and every evidence item against v2 invariants."""
    from .extraction import ReportLabelExtractor

    issue_columns = [
        "check", "severity", "StudyInstanceUID", "target", "status", "rationale", "detail",
    ]
    issues: list[dict[str, object]] = []
    reports = train.assign(StudyInstanceUID=train["StudyInstanceUID"].astype(str)).set_index("StudyInstanceUID")["Report"]
    extractor = ReportLabelExtractor()

    checks = {
        "unique_study_target": (len(long_labels), "error"),
        "policy_version": (len(long_labels), "error"),
        "evidence_json_schema": (len(long_labels), "error"),
        "evidence_in_diagnostic_clause": (len(long_labels), "error"),
        "status_value_schema": (len(long_labels), "error"),
        "rationale_confidence_schema": (len(long_labels), "error"),
        "final_provenance_schema": (len(long_labels), "error"),
        "decisive_status_visible_in_evidence": (int(long_labels["status"].ne("unknown").sum()), "error"),
        "conflict_visible_in_evidence": (int(long_labels["rationale"].str.contains("conflict|retained with negative", regex=True).sum()), "warning"),
        "rationale_evidence_mode": (int(long_labels["status"].ne("unknown").sum()), "warning"),
    }

    def add(check: str, row: object, detail: str) -> None:
        issues.append({
            "check": check,
            "severity": checks[check][1],
            "StudyInstanceUID": str(row.StudyInstanceUID),
            "target": str(row.target),
            "status": str(row.status),
            "rationale": str(row.rationale),
            "detail": detail[:1000],
        })

    duplicated = long_labels.duplicated(["StudyInstanceUID", "target"], keep=False)
    for row in long_labels[duplicated].itertuples(index=False):
        add("unique_study_target", row, "duplicate StudyInstanceUID-target pair")

    @lru_cache(maxsize=None)
    def diagnostic_clauses(uid: str) -> tuple[str, ...]:
        return tuple(clause.text for clause in segment_report(reports.get(uid, "")) if clause.diagnostic)

    @lru_cache(maxsize=None)
    def isolated_result(target: str, evidence: str) -> tuple[str, str]:
        result = extractor.extract(f"Findings: {evidence}")[target]
        return result.status, result.rationale

    rationale_contract = {
        "no reliable target-specific evidence": ("unknown", 0.0),
        "explicit positive evidence": ("positive", 0.90),
        "positive evidence retained with conflicting mentions": ("positive", 0.70),
        "explicit collective positive evidence": ("positive", 0.80),
        "collective positive evidence retained with conflicting mentions": ("positive", 0.65),
        "explicit uncertain evidence": ("uncertain", 0.50),
        "explicit uncertain evidence retained with negative mentions": ("uncertain", 0.50),
        "explicit collective uncertain evidence": ("uncertain", 0.45),
        "explicit collective uncertain evidence retained with negative mentions": ("uncertain", 0.45),
        "explicit negation or normality": ("negative", 0.85),
        "explicit collective negation or normality": ("negative", 0.75),
    }

    for row in long_labels.itertuples(index=False):
        if row.policy_version != POLICY_VERSION:
            add("policy_version", row, f"observed={row.policy_version}; expected={POLICY_VERSION}")

        try:
            evidence = json.loads(row.evidence)
        except (TypeError, json.JSONDecodeError) as exc:
            add("evidence_json_schema", row, f"invalid JSON: {exc}")
            evidence = []
        if not isinstance(evidence, list) or not all(isinstance(item, str) and item for item in evidence):
            add("evidence_json_schema", row, "evidence must be a JSON list of non-empty strings")
            evidence = []
        elif len(evidence) > 3 or len(evidence) != len(set(evidence)):
            add("evidence_json_schema", row, "evidence must contain at most three unique clauses")

        diagnostic = diagnostic_clauses(str(row.StudyInstanceUID))
        for item in evidence:
            if not any(clause.startswith(item) for clause in diagnostic):
                add("evidence_in_diagnostic_clause", row, f"not found in diagnostic clauses: {item}")

        label_missing = pd.isna(row.derived_label)
        score_missing = pd.isna(row.derived_score)
        valid_status_values = (
            (row.status == "positive" and row.derived_label == 1 and not score_missing and row.derived_score > 0)
            or (row.status == "negative" and row.derived_label == 0 and row.derived_score == 0)
            or (row.status == "uncertain" and label_missing and not score_missing)
            or (row.status == "unknown" and label_missing and score_missing)
        )
        if not valid_status_values or (row.status == "unknown") != (not evidence):
            add("status_value_schema", row, "status, derived label/score and evidence are inconsistent")

        expected = rationale_contract.get(row.rationale)
        if expected is None or row.status != expected[0] or not math.isclose(float(row.confidence), expected[1]):
            add("rationale_confidence_schema", row, "rationale, status and confidence do not follow the v2 contract")

        official_missing = pd.isna(row.official_label)
        final_missing = pd.isna(row.final_label)
        provenance_ok = (
            (not official_missing and row.final_source == "official" and row.final_label == row.official_label)
            or (official_missing and not label_missing and row.final_source == "report_derived" and row.final_label == row.derived_label)
            or (official_missing and label_missing and row.final_source == "unresolved" and final_missing)
        )
        if not provenance_ok:
            add("final_provenance_schema", row, "official/derived/final values do not match final_source")

        if row.status != "unknown" and evidence:
            isolated = [isolated_result(str(row.target), item) for item in evidence]
            if not any(status == row.status for status, _ in isolated):
                add("decisive_status_visible_in_evidence", row, f"isolated statuses={isolated}")
            conflict_expected = "conflict" in row.rationale or "retained with negative" in row.rationale
            if conflict_expected and not any(status not in {row.status, "unknown"} for status, _ in isolated):
                add("conflict_visible_in_evidence", row, f"isolated statuses={isolated}")
            collective_expected = "collective" in row.rationale
            same_status_modes = [rationale for status, rationale in isolated if status == row.status]
            if same_status_modes and collective_expected != all("collective" in value for value in same_status_modes):
                add("rationale_evidence_mode", row, f"isolated rationales={same_status_modes}")

    detail = pd.DataFrame(issues, columns=issue_columns)
    summary_rows: list[dict[str, object]] = []
    for check, (evaluated_rows, severity) in checks.items():
        part = detail[detail["check"].eq(check)] if not detail.empty else detail
        summary_rows.append({
            "check": check,
            "severity": severity,
            "evaluated_rows": evaluated_rows,
            "issue_count": len(part),
            "issue_rate": len(part) / evaluated_rows if evaluated_rows else 0.0,
            "example_study_targets": "; ".join(
                f"{row.StudyInstanceUID}|{row.target}" for row in part.head(3).itertuples(index=False)
            ),
        })
    return pd.DataFrame(summary_rows), detail
