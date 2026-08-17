"""Descriptive, corpus-only inspection of report-label policy v3.

This module reconstructs the runtime units exposed by the current v3 code and
summarises them without changing policy behaviour, derived labels, or official
overrides.  All metrics use report-derived ``status`` and provenance only.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path
import random
import re
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

from ..constants import (
    NEGATION_TERMS,
    NORMALITY_TERMS,
    POSTPOSED_NEGATION_TERMS,
    TARGETS,
    UNCERTAINTY_TERMS,
)
from ..pipeline import _portable_path, _sha256
from ..text import matching_terms, normalize_text, segment_report
from .constants import POLICY_VERSION
from .evaluation import exact_template_consistency
from .extraction import V3ReportLabelExtractor, _V3_UNCERTAINTY, report_sha256
from .reconciliation import build_propositions
from .text import build_text_views, language_hypotheses


INSPECTION_VERSION = "report-label-corpus-inspection-v1.0.0"
VALID_STATUSES = ("positive", "negative", "uncertain", "unknown")
BINARY_STATUSES = ("positive", "negative")
SIMPLE_TOKEN_PATTERN = re.compile(r"\b\w+\b", flags=re.UNICODE)
NUMBER_PATTERN = re.compile(r"\b\d+(?:[.,]\d+)*\b")

OUTPUT_FILES = {
    "corpus_unit_counts": "corpus_unit_counts.csv",
    "text_length_summary": "text_length_summary.csv",
    "target_status_summary": "target_status_summary.csv",
    "language_summary": "language_summary.csv",
    "language_hypothesis_summary": "language_hypothesis_summary.csv",
    "language_target_status_summary": "language_target_status_summary.csv",
    "detector_summary": "detector_summary.csv",
    "detector_combination_summary": "detector_combination_summary.csv",
    "confidence_summary": "confidence_summary.csv",
    "phenotype_summary": "phenotype_summary.csv",
    "target_phenotype_status": "target_phenotype_status.csv",
    "rule_summary": "rule_summary.csv",
    "duplicate_summary": "duplicate_summary.csv",
    "duplicate_group_size_distribution": "duplicate_group_size_distribution.csv",
    "duplicate_groups": "duplicate_groups.csv",
    "template_family_summary": "template_family_summary.csv",
    "lexical_diversity_summary": "lexical_diversity_summary.csv",
    "ngram_summary": "ngram_summary.csv",
    "text_similarity_summary": "text_similarity_summary.csv",
    "evidence_target_status_summary": "evidence_target_status_summary.csv",
    "evidence_inventory": "evidence_inventory.csv",
    "conflict_cases": "conflict_cases.csv",
    "collective_evidence_summary": "collective_evidence_summary.csv",
    "view_kind_summary": "view_kind_summary.csv",
    "linked_view_dependency_cases": "linked_view_dependency_cases.csv",
    "context_structure_summary": "context_structure_summary.csv",
    "negation_summary": "negation_summary.csv",
    "uncertain_summary": "uncertain_summary.csv",
    "unknown_summary": "unknown_summary.csv",
    "clause_usage_summary": "clause_usage_summary.csv",
    "study_level_distribution": "study_level_distribution.csv",
    "target_cooccurrence": "target_cooccurrence.csv",
    "effective_example_structure": "effective_example_structure.csv",
    "audit_sample": "audit_sample.csv",
    "metadata": "inspection_run_metadata.json",
}


@dataclass(frozen=True)
class InspectionParameters:
    """Explicit parameters that affect semantic inspection artifacts."""

    seed: int = 20260817
    audit_sample_max_rows: int = 600
    similarity_max_pairs_per_stratum: int = 20_000
    ngram_top_k: int = 100
    duplicate_group_text_limit: int = 1_000

    def as_dict(self) -> dict[str, int]:
        return {
            "seed": self.seed,
            "audit_sample_max_rows": self.audit_sample_max_rows,
            "similarity_max_pairs_per_stratum": self.similarity_max_pairs_per_stratum,
            "ngram_top_k": self.ngram_top_k,
            "duplicate_group_text_limit": self.duplicate_group_text_limit,
        }


def simple_tokens(value: object) -> list[str]:
    """Unicode word-token baseline used only for descriptive counts."""
    return SIMPLE_TOKEN_PATTERN.findall(normalize_text(value))


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _json_list(values: Iterable[object]) -> str:
    return _json(sorted({str(value) for value in values if value not in (None, "")}))


def _safe_json_list(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    if not isinstance(value, str) or not value:
        return []
    parsed = json.loads(value)
    if not isinstance(parsed, list):
        raise ValueError("expected a JSON list")
    return parsed


def _stable_hash(seed: int, *values: object) -> str:
    payload = "|".join([str(seed), *(str(value) for value in values)])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _group_hash(level: str, text: str) -> str:
    return hashlib.sha256(f"{level}:{text}".encode("utf-8")).hexdigest()


def _support_scope(view_kinds: Sequence[str]) -> str:
    kinds = set(view_kinds)
    if kinds == {"strict"}:
        return "strict_only"
    if kinds == {"linked"}:
        return "linked_only"
    if kinds == {"strict", "linked"}:
        return "strict_and_linked"
    return "none"


def _resolution_mode(rationale: str) -> str:
    if "collective" in rationale:
        return "collective"
    if "target-specific" in rationale:
        return "target_specific"
    return "unknown"


def validate_inspection_inputs(
    train: pd.DataFrame,
    supervision: pd.DataFrame,
    expected_studies: int,
) -> None:
    """Validate source cardinalities without consulting official label values."""
    required_train = {"StudyInstanceUID", "Report"}
    required_supervision = {
        "StudyInstanceUID", "report_sha256", "language_group", "target", "status",
        "derived_label", "confidence", "evidence", "rationale", "phenotypes",
        "detectors", "evidence_provenance", "policy_version",
    }
    if missing := required_train - set(train.columns):
        raise ValueError(f"train is missing columns: {sorted(missing)}")
    if missing := required_supervision - set(supervision.columns):
        raise ValueError(f"supervision is missing columns: {sorted(missing)}")
    if len(train) != expected_studies or train["StudyInstanceUID"].astype(str).nunique() != expected_studies:
        raise ValueError("unexpected report/StudyInstanceUID cardinality")
    if len(supervision) != expected_studies * len(TARGETS):
        raise ValueError("unexpected Study-target cardinality")
    if supervision.duplicated(["StudyInstanceUID", "target"]).any():
        raise ValueError("Study-target rows are not unique")
    if set(supervision["target"]) != set(TARGETS):
        raise ValueError("supervision targets differ from policy targets")
    if not set(supervision["status"]).issubset(VALID_STATUSES):
        raise ValueError("supervision contains invalid status values")
    if set(supervision["policy_version"]) != {POLICY_VERSION}:
        raise ValueError("supervision policy version differs from executable v3")
    train_uids = set(train["StudyInstanceUID"].astype(str))
    supervision_uids = set(supervision["StudyInstanceUID"].astype(str))
    if train_uids != supervision_uids:
        raise ValueError("StudyInstanceUID population differs between train and supervision")
    hashes = train[["StudyInstanceUID", "Report"]].copy()
    hashes["StudyInstanceUID"] = hashes["StudyInstanceUID"].astype(str)
    hashes["expected_hash"] = hashes["Report"].map(report_sha256)
    observed = supervision[["StudyInstanceUID", "report_sha256"]].drop_duplicates()
    checked = hashes.merge(observed, on="StudyInstanceUID", validate="one_to_one")
    if not checked["expected_hash"].eq(checked["report_sha256"]).all():
        raise ValueError("report hashes differ between train and v3 supervision")


def reconstruct_runtime_units(
    train: pd.DataFrame,
    extractor: V3ReportLabelExtractor | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Reconstruct Reports, TextViews, Mentions, and Propositions from current v3 code."""
    extractor = extractor or V3ReportLabelExtractor()
    report_rows: list[dict[str, object]] = []
    view_rows: list[dict[str, object]] = []
    mention_rows: list[dict[str, object]] = []
    proposition_rows: list[dict[str, object]] = []

    for record in train[["StudyInstanceUID", "Report"]].to_dict("records"):
        uid = str(record["StudyInstanceUID"])
        report = record["Report"] if isinstance(record["Report"], str) else ""
        hypotheses = language_hypotheses(report)
        primary_language = hypotheses[0] if hypotheses else "empty"
        views = build_text_views(report)
        mentions = list(extractor.mentions(report))
        propositions = build_propositions(mentions)
        strict_count = sum(view.kind == "strict" for view in views)
        linked_count = sum(view.kind == "linked" for view in views)
        report_rows.append({
            "StudyInstanceUID": uid,
            "Report": report,
            "normalized_text": normalize_text(report),
            "report_sha256": report_sha256(report),
            "language_group": primary_language,
            "language_hypotheses": _json(list(hypotheses)),
            "characters": len(report),
            "simple_tokens": len(simple_tokens(report)),
            "clauses": strict_count,
            "strict_views": strict_count,
            "linked_views": linked_count,
        })
        for index, view in enumerate(views):
            view_id = f"{uid}:view:{index:04d}"
            view_rows.append({
                "StudyInstanceUID": uid,
                "view_id": view_id,
                "view_kind": view.kind,
                "text": view.text,
                "normalized_text": normalize_text(view.text),
                "section": view.section,
                "diagnostic": bool(view.diagnostic),
                "source_indices": _json(list(view.source_indices)),
                "source_clause_count": len(view.source_indices),
                "language_group": primary_language,
                "characters": len(view.text),
                "simple_tokens": len(simple_tokens(view.text)),
            })
        for index, mention in enumerate(mentions):
            mention_rows.append({
                "StudyInstanceUID": uid,
                "mention_id": f"{uid}:mention:{index:05d}",
                "target": mention.target,
                "status": mention.status,
                "phenotype": mention.phenotype,
                "text": mention.text,
                "normalized_text": normalize_text(mention.text),
                "detector": mention.detector,
                "view_kind": mention.view_kind,
                "language": mention.language,
                "report_language_group": primary_language,
                "confidence": float(mention.confidence),
                "section": mention.section,
                "source_indices": _json(list(mention.source_indices)),
                "source_clause_count": len(mention.source_indices),
                "span": _json(list(mention.span)) if mention.span else "[]",
                "collective": bool(mention.collective),
                "rule": mention.rule or "<no_explicit_rule>",
            })
        for index, proposition in enumerate(propositions):
            proposition_rows.append({
                "StudyInstanceUID": uid,
                "proposition_id": f"{uid}:proposition:{index:05d}",
                "target": proposition.target,
                "status": proposition.status,
                "phenotype": proposition.phenotype,
                "evidence": proposition.evidence,
                "normalized_evidence": normalize_text(proposition.evidence),
                "detectors": _json(list(proposition.detectors)),
                "detector_combination": "|".join(proposition.detectors),
                "detector_count": len(proposition.detectors),
                "view_kinds": _json(list(proposition.view_kinds)),
                "view_support": _support_scope(proposition.view_kinds),
                "languages": _json(list(proposition.languages)),
                "language_combination": "|".join(proposition.languages),
                "report_language_group": primary_language,
                "sections": _json(list(proposition.sections)),
                "source_indices": _json(list(proposition.source_indices)),
                "source_clause_count": len(proposition.source_indices),
                "spans": _json([list(span) for span in proposition.spans]),
                "confidence": float(proposition.confidence),
                "collective": bool(proposition.collective),
                "rules": _json(list(proposition.rules)),
                "rule_combination": "|".join(proposition.rules) or "<no_explicit_rule>",
            })
    return (
        pd.DataFrame(report_rows),
        pd.DataFrame(view_rows),
        pd.DataFrame(mention_rows),
        pd.DataFrame(proposition_rows),
    )


def build_evidence_inventory(
    supervision: pd.DataFrame,
    reports: pd.DataFrame,
) -> pd.DataFrame:
    """Explode selected provenance into one auditable row per selected proposition."""
    report_lookup = reports.set_index("StudyInstanceUID")
    rows: list[dict[str, object]] = []
    for row in supervision.itertuples(index=False):
        provenance = _safe_json_list(row.evidence_provenance)
        for order, item in enumerate(provenance):
            if not isinstance(item, dict):
                raise ValueError("evidence_provenance must contain objects")
            detectors = [str(value) for value in item.get("detectors", [])]
            views = [str(value) for value in item.get("views", [])]
            languages = [str(value) for value in item.get("languages", [])]
            rules = [str(value) for value in item.get("rules", [])]
            evidence = str(item.get("evidence", ""))
            source_indices = [int(value) for value in item.get("source_indices", [])]
            proposition_status = str(item.get("status", ""))
            uid = str(row.StudyInstanceUID)
            rows.append({
                "StudyInstanceUID": uid,
                "target": row.target,
                "final_status": row.status,
                "selected_order": order,
                "proposition_status": proposition_status,
                "is_winning_status": proposition_status == row.status,
                "evidence": evidence,
                "normalized_evidence": normalize_text(evidence),
                "phenotype": str(item.get("phenotype", "")),
                "detectors": _json(detectors),
                "detector_combination": "|".join(detectors),
                "detector_count": len(detectors),
                "views": _json(views),
                "view_support": _support_scope(views),
                "languages": _json(languages),
                "language_combination": "|".join(languages),
                "sections": _json(item.get("sections", [])),
                "source_indices": _json(source_indices),
                "source_clause_count": len(source_indices),
                "spans": _json(item.get("spans", [])),
                "proposition_confidence": float(item.get("confidence", 0.0)),
                "final_confidence": float(row.confidence),
                "collective": bool(item.get("collective", False)),
                "rules": _json(rules),
                "rule_combination": "|".join(rules) or "<no_explicit_rule>",
                "report_language_group": row.language_group,
                "rationale": row.rationale,
                "has_conflict": "conflict" in str(row.rationale),
                "resolution_mode": _resolution_mode(str(row.rationale)),
                "characters": len(evidence),
                "simple_tokens": len(simple_tokens(evidence)),
                "report_sha256": report_lookup.at[uid, "report_sha256"],
            })
    columns = [
        "StudyInstanceUID", "target", "final_status", "selected_order",
        "proposition_status", "is_winning_status", "evidence", "normalized_evidence",
        "phenotype", "detectors", "detector_combination", "detector_count", "views",
        "view_support", "languages", "language_combination", "sections",
        "source_indices", "source_clause_count", "spans", "proposition_confidence",
        "final_confidence", "collective", "rules", "rule_combination",
        "report_language_group", "rationale", "has_conflict", "resolution_mode",
        "characters", "simple_tokens", "report_sha256",
    ]
    return pd.DataFrame(rows, columns=columns)


def validate_runtime_reconciliation(
    supervision: pd.DataFrame,
    reports: pd.DataFrame,
    propositions: pd.DataFrame,
    evidence: pd.DataFrame,
) -> None:
    """Reconcile reconstructed units with the persisted v3 artifact."""
    if len(supervision) != len(reports) * len(TARGETS):
        raise ValueError("Study-target denominator does not reconcile")
    expected_selected = int(supervision["evidence_provenance"].map(lambda value: len(_safe_json_list(value))).sum())
    if len(evidence) != expected_selected:
        raise ValueError("selected evidence count does not reconcile with provenance")
    proposition_keys = set(zip(
        propositions["StudyInstanceUID"], propositions["target"], propositions["status"],
        propositions["phenotype"], propositions["evidence"],
    ))
    selected_keys = set(zip(
        evidence["StudyInstanceUID"], evidence["target"], evidence["proposition_status"],
        evidence["phenotype"], evidence["evidence"],
    ))
    if not selected_keys.issubset(proposition_keys):
        missing = len(selected_keys - proposition_keys)
        raise ValueError(f"{missing} selected provenance keys are absent from reconstructed propositions")
    if not evidence[evidence["is_winning_status"]].groupby(["StudyInstanceUID", "target"]).size().index.is_unique:
        raise ValueError("unexpected non-unique winning evidence group index")


def _describe(values: pd.Series) -> dict[str, object]:
    numeric = pd.to_numeric(values, errors="coerce").dropna().astype(float)
    if numeric.empty:
        return {
            "count": 0, "mean": np.nan, "std": np.nan, "median": np.nan,
            "min": np.nan, "max": np.nan, "p05": np.nan, "p25": np.nan,
            "p75": np.nan, "p95": np.nan, "p99": np.nan,
        }
    return {
        "count": len(numeric),
        "mean": numeric.mean(),
        "std": numeric.std(ddof=1),
        "median": numeric.median(),
        "min": numeric.min(),
        "max": numeric.max(),
        "p05": numeric.quantile(0.05),
        "p25": numeric.quantile(0.25),
        "p75": numeric.quantile(0.75),
        "p95": numeric.quantile(0.95),
        "p99": numeric.quantile(0.99),
    }


def corpus_unit_counts(
    reports: pd.DataFrame,
    views: pd.DataFrame,
    mentions: pd.DataFrame,
    propositions: pd.DataFrame,
    evidence: pd.DataFrame,
    supervision: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    def add(unit: str, count: int, target: str = "__all__", status: str = "__all__", denominator: str = "instances") -> None:
        rows.append({"unit": unit, "target": target, "status": status, "count": int(count), "denominator": denominator})

    add("Report", len(reports), denominator="Reports")
    add("clause", int(views["view_kind"].eq("strict").sum()), denominator="strict TextViews produced by segment_report")
    add("strict TextView", int(views["view_kind"].eq("strict").sum()), denominator="TextViews")
    add("linked TextView", int(views["view_kind"].eq("linked").sum()), denominator="TextViews")
    add("Mention", len(mentions), denominator="Mentions before deduplication")
    add("Proposition", len(propositions), denominator="deduplicated Propositions")
    add("selected evidence", len(evidence), denominator="selected provenance entries, including retained conflicts")
    add(
        "selected winning evidence",
        int(evidence["is_winning_status"].sum()),
        denominator="selected provenance entries matching the final status",
    )
    add("Study-target pair", len(supervision), denominator="Study × target pairs")
    for status in VALID_STATUSES:
        add("Study-target pair", int(supervision["status"].eq(status).sum()), status=status, denominator="Study × target pairs")
    add("binary resolved Study-target pair", int(supervision["status"].isin(BINARY_STATUSES).sum()), denominator="Study × target pairs")
    for target in TARGETS:
        add("Mention", int(mentions["target"].eq(target).sum()), target=target, denominator="Mentions")
        add("Proposition", int(propositions["target"].eq(target).sum()), target=target, denominator="Propositions")
        add("selected evidence", int(evidence["target"].eq(target).sum()), target=target, denominator="selected provenance entries")
        add(
            "selected winning evidence",
            int((evidence["target"].eq(target) & evidence["is_winning_status"]).sum()),
            target=target,
            denominator="selected provenance entries matching the final status",
        )
        part = supervision[supervision["target"].eq(target)]
        for status in VALID_STATUSES:
            add("Study-target pair", int(part["status"].eq(status).sum()), target=target, status=status, denominator=f"{len(part)} pairs for target")
        add("binary resolved Study-target pair", int(part["status"].isin(BINARY_STATUSES).sum()), target=target, denominator=f"{len(part)} pairs for target")
    for column, unit in (
        ("clauses", "clauses per Report"),
        ("strict_views", "strict TextViews per Report"),
        ("linked_views", "linked TextViews per Report"),
    ):
        rows.append({
            "unit": unit,
            "target": "__all__",
            "status": "__all__",
            "denominator": "Reports",
            **_describe(reports[column]),
        })
    return pd.DataFrame(rows)


def text_length_summary(
    reports: pd.DataFrame,
    views: pd.DataFrame,
    evidence: pd.DataFrame,
) -> pd.DataFrame:
    units = {
        "Report": reports,
        "strict TextView": views[views["view_kind"].eq("strict")],
        "linked TextView": views[views["view_kind"].eq("linked")],
        "selected evidence": evidence,
    }
    rows = []
    for unit, frame in units.items():
        for measure in ("characters", "simple_tokens"):
            rows.append({"unit": unit, "measure": measure, **_describe(frame[measure])})
    return pd.DataFrame(rows)


def target_status_summary(supervision: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for target in TARGETS:
        part = supervision[supervision["target"].eq(target)]
        counts = part["status"].value_counts()
        positive = int(counts.get("positive", 0))
        negative = int(counts.get("negative", 0))
        resolved = positive + negative
        rows.append({
            "target": target,
            "pairs": len(part),
            "positive": positive,
            "positive_rate": positive / len(part),
            "negative": negative,
            "negative_rate": negative / len(part),
            "uncertain": int(counts.get("uncertain", 0)),
            "uncertain_rate": counts.get("uncertain", 0) / len(part),
            "unknown": int(counts.get("unknown", 0)),
            "unknown_rate": counts.get("unknown", 0) / len(part),
            "binary_resolved": resolved,
            "binary_resolved_rate": resolved / len(part),
            "positive_over_binary_resolved": positive / resolved if resolved else np.nan,
            "negative_over_binary_resolved": negative / resolved if resolved else np.nan,
        })
    return pd.DataFrame(rows)


def language_tables(
    reports: pd.DataFrame,
    views: pd.DataFrame,
    mentions: pd.DataFrame,
    propositions: pd.DataFrame,
    supervision: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows = []
    for language, report_part in reports.groupby("language_group", sort=True):
        uids = set(report_part["StudyInstanceUID"])
        pair_part = supervision[supervision["StudyInstanceUID"].isin(uids)]
        status = pair_part["status"].value_counts()
        rows.append({
            "language_group": language,
            "reports": len(report_part),
            "study_target_pairs": len(pair_part),
            "positive": int(status.get("positive", 0)),
            "negative": int(status.get("negative", 0)),
            "uncertain": int(status.get("uncertain", 0)),
            "unknown": int(status.get("unknown", 0)),
            "binary_resolved": int(pair_part["status"].isin(BINARY_STATUSES).sum()),
            "resolved_rate": pair_part["status"].isin(BINARY_STATUSES).mean(),
            "strict_views": int((views["StudyInstanceUID"].isin(uids) & views["view_kind"].eq("strict")).sum()),
            "linked_views": int((views["StudyInstanceUID"].isin(uids) & views["view_kind"].eq("linked")).sum()),
            "mentions": int(mentions["StudyInstanceUID"].isin(uids).sum()),
            "propositions": int(propositions["StudyInstanceUID"].isin(uids).sum()),
        })
    language_summary = pd.DataFrame(rows)

    exploded_hypotheses = []
    for row in reports.itertuples(index=False):
        for hypothesis in _safe_json_list(row.language_hypotheses):
            exploded_hypotheses.append({"StudyInstanceUID": row.StudyInstanceUID, "language_hypothesis": hypothesis})
    hypothesis_map = pd.DataFrame(exploded_hypotheses)
    hypothesis_rows = []
    for hypothesis, part in hypothesis_map.groupby("language_hypothesis", sort=True):
        uids = set(part["StudyInstanceUID"])
        pairs = supervision[supervision["StudyInstanceUID"].isin(uids)]
        status = pairs["status"].value_counts()
        hypothesis_rows.append({
            "language_hypothesis": hypothesis,
            "reports": len(uids),
            "study_target_pairs": len(pairs),
            "positive": int(status.get("positive", 0)),
            "negative": int(status.get("negative", 0)),
            "uncertain": int(status.get("uncertain", 0)),
            "unknown": int(status.get("unknown", 0)),
            "resolved_rate": pairs["status"].isin(BINARY_STATUSES).mean(),
            "strict_views": int((views["StudyInstanceUID"].isin(uids) & views["view_kind"].eq("strict")).sum()),
            "linked_views": int((views["StudyInstanceUID"].isin(uids) & views["view_kind"].eq("linked")).sum()),
            "mentions": int(mentions["StudyInstanceUID"].isin(uids).sum()),
            "propositions": int(propositions["StudyInstanceUID"].isin(uids).sum()),
            "non_exclusive_denominator": "Reports may contribute to more than one hypothesis",
        })
    hypothesis_summary = pd.DataFrame(hypothesis_rows)

    language_target_rows = []
    for (language, target), part in supervision.groupby(["language_group", "target"], sort=True):
        status = part["status"].value_counts()
        resolved = int(part["status"].isin(BINARY_STATUSES).sum())
        language_target_rows.append({
            "language_group": language,
            "target": target,
            "pairs": len(part),
            "positive": int(status.get("positive", 0)),
            "negative": int(status.get("negative", 0)),
            "uncertain": int(status.get("uncertain", 0)),
            "unknown": int(status.get("unknown", 0)),
            "binary_resolved": resolved,
            "resolved_rate": resolved / len(part),
        })
    return language_summary, hypothesis_summary, pd.DataFrame(language_target_rows)


def detector_tables(
    mentions: pd.DataFrame,
    propositions: pd.DataFrame,
    evidence: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Describe detector participation without treating overlaps as independent labels."""
    rows: list[dict[str, object]] = []
    mention_group = ["detector", "target", "status", "phenotype", "language", "rule"]
    for detector, part in mentions.groupby("detector", sort=True):
        rows.append({
            "unit": "mention",
            "detector": detector,
            "target": "__all__",
            "status": "__all__",
            "phenotype": "__all__",
            "language": "__all__",
            "rule": "__all__",
            "count": len(part),
            "unique_studies": part["StudyInstanceUID"].nunique(),
            "unique_study_target_pairs": part[["StudyInstanceUID", "target"]].drop_duplicates().shape[0],
            "non_additivity_note": "Overall detector total; detector participation counts can overlap.",
        })
    for key, part in mentions.groupby(mention_group, dropna=False, sort=True):
        rows.append({
            "unit": "mention",
            **dict(zip(mention_group, key)),
            "count": len(part),
            "unique_studies": part["StudyInstanceUID"].nunique(),
            "unique_study_target_pairs": part[["StudyInstanceUID", "target"]].drop_duplicates().shape[0],
            "non_additivity_note": "Detector participation counts can overlap.",
        })

    prop_rows = []
    for prop in propositions.itertuples(index=False):
        for detector in _safe_json_list(prop.detectors):
            prop_rows.append({
                "StudyInstanceUID": prop.StudyInstanceUID,
                "proposition_id": prop.proposition_id,
                "detector": detector,
                "target": prop.target,
                "status": prop.status,
                "phenotype": prop.phenotype,
                "language": prop.language_combination or "<none>",
                "rule": prop.rule_combination,
            })
    prop_participation = pd.DataFrame(prop_rows)
    group = ["detector", "target", "status", "phenotype", "language", "rule"]
    for detector, part in prop_participation.groupby("detector", sort=True):
        rows.append({
            "unit": "proposition_participation",
            "detector": detector,
            "target": "__all__",
            "status": "__all__",
            "phenotype": "__all__",
            "language": "__all__",
            "rule": "__all__",
            "count": part["proposition_id"].nunique(),
            "unique_studies": part["StudyInstanceUID"].nunique(),
            "unique_study_target_pairs": part[["StudyInstanceUID", "target"]].drop_duplicates().shape[0],
            "non_additivity_note": "Overall detector total; a Proposition may have multiple detectors.",
        })
    for key, part in prop_participation.groupby(group, dropna=False, sort=True):
        rows.append({
            "unit": "proposition_participation",
            **dict(zip(group, key)),
            "count": part["proposition_id"].nunique(),
            "unique_studies": part["StudyInstanceUID"].nunique(),
            "unique_study_target_pairs": part[["StudyInstanceUID", "target"]].drop_duplicates().shape[0],
            "non_additivity_note": "A Proposition may be supported by multiple detectors.",
        })

    selected_rows = []
    for item in evidence.itertuples(index=False):
        for detector in _safe_json_list(item.detectors):
            selected_rows.append({
                "StudyInstanceUID": item.StudyInstanceUID,
                "detector": detector,
                "target": item.target,
                "status": item.proposition_status,
                "phenotype": item.phenotype,
                "language": item.language_combination or "<none>",
                "rule": item.rule_combination,
                "is_winning_status": item.is_winning_status,
            })
    selected_participation = pd.DataFrame(selected_rows)
    for unit, selected in (
        ("selected_pair_participation", selected_participation),
        ("selected_winning_pair_participation", selected_participation[selected_participation["is_winning_status"]]),
    ):
        for detector, part in selected.groupby("detector", sort=True):
            pair_count = part[["StudyInstanceUID", "target"]].drop_duplicates().shape[0]
            rows.append({
                "unit": unit,
                "detector": detector,
                "target": "__all__",
                "status": "__all__",
                "phenotype": "__all__",
                "language": "__all__",
                "rule": "__all__",
                "count": pair_count,
                "unique_studies": part["StudyInstanceUID"].nunique(),
                "unique_study_target_pairs": pair_count,
                "non_additivity_note": "Overall detector participation; pairs may participate in multiple detectors.",
            })
        for key, part in selected.groupby(group, dropna=False, sort=True):
            rows.append({
                "unit": unit,
                **dict(zip(group, key)),
                "count": part[["StudyInstanceUID", "target"]].drop_duplicates().shape[0],
                "unique_studies": part["StudyInstanceUID"].nunique(),
                "unique_study_target_pairs": part[["StudyInstanceUID", "target"]].drop_duplicates().shape[0],
                "non_additivity_note": "A selected pair may include multiple detectors/propositions.",
            })
    detector_summary = pd.DataFrame(rows).sort_values(
        ["unit", "count", "detector", "target"], ascending=[True, False, True, True],
    )

    selected_keys = set(zip(
        evidence["StudyInstanceUID"], evidence["target"], evidence["proposition_status"],
        evidence["phenotype"], evidence["evidence"],
    ))
    combination_rows = []
    for combination, part in propositions.groupby("detector_combination", sort=True):
        detector_count = int(part["detector_count"].iloc[0])
        selected_count = sum(
            (row.StudyInstanceUID, row.target, row.status, row.phenotype, row.evidence) in selected_keys
            for row in part.itertuples(index=False)
        )
        combination_rows.append({
            "detector_combination": combination,
            "detector_count": detector_count,
            "detector_count_bucket": "3+" if detector_count >= 3 else str(detector_count),
            "propositions": len(part),
            "selected_propositions": selected_count,
            "unique_studies": part["StudyInstanceUID"].nunique(),
            "targets": _json_list(part["target"]),
            "statuses": _json_list(part["status"]),
            "phenotypes": _json_list(part["phenotype"]),
        })
    detector_combinations = pd.DataFrame(combination_rows).sort_values(
        ["propositions", "detector_combination"], ascending=[False, True],
    )
    return detector_summary, detector_combinations


def _confidence_rows(
    frame: pd.DataFrame,
    unit: str,
    confidence_column: str,
    dimensions: Sequence[str],
) -> list[dict[str, object]]:
    rows = []

    def add(dimension: str, value: object, part: pd.DataFrame) -> None:
        stats = _describe(part[confidence_column])
        rows.append({
            "unit": unit,
            "dimension": dimension,
            "value": str(value),
            **stats,
            "unique_confidence_values": _json(sorted(pd.to_numeric(part[confidence_column]).dropna().unique().tolist())),
            "interpretation": "deterministic evidence-strength rank; not a calibrated probability",
        })

    add("overall", "__all__", frame)
    for value, part in frame.groupby(confidence_column, dropna=False, sort=True):
        add("confidence_value", value, part)
    for dimension in dimensions:
        for value, part in frame.groupby(dimension, dropna=False, sort=True):
            add(dimension, value, part)
    return rows


def confidence_summary(
    supervision: pd.DataFrame,
    evidence: pd.DataFrame,
) -> pd.DataFrame:
    final_pairs = supervision.copy()
    final_pairs["has_conflict"] = final_pairs["rationale"].str.contains("conflict", regex=False)
    final_pairs["resolution_mode"] = final_pairs["rationale"].map(_resolution_mode)
    rows = _confidence_rows(
        final_pairs,
        "Study-target pair",
        "confidence",
        ["target", "status", "language_group", "has_conflict", "resolution_mode"],
    )
    selected = evidence.copy()
    selected["detector"] = selected["detector_combination"]
    selected["rule"] = selected["rule_combination"]
    selected["language"] = selected["language_combination"]
    rows.extend(_confidence_rows(
        selected,
        "selected Proposition",
        "proposition_confidence",
        ["target", "proposition_status", "detector", "rule", "phenotype", "language", "collective", "view_support"],
    ))
    for dimension, json_column in (("detector", "detectors"), ("rule", "rules"), ("language", "languages")):
        participation_rows = []
        for item in evidence.itertuples(index=False):
            values = _safe_json_list(getattr(item, json_column))
            if dimension == "rule" and not values:
                values = ["<no_explicit_rule>"]
            for value in values:
                participation_rows.append({
                    dimension: value,
                    "proposition_confidence": item.proposition_confidence,
                    "StudyInstanceUID": item.StudyInstanceUID,
                    "target": item.target,
                })
        participation = pd.DataFrame(participation_rows)
        if not participation.empty:
            extra = _confidence_rows(
                participation,
                f"selected Proposition {dimension} participation",
                "proposition_confidence",
                [dimension],
            )
            rows.extend(row for row in extra if row["dimension"] == dimension)
    return pd.DataFrame(rows)


def phenotype_tables(
    propositions: pd.DataFrame,
    evidence: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for phenotype, part in propositions.groupby("phenotype", sort=True):
        selected = evidence[evidence["phenotype"].eq(phenotype)]
        winning = selected[selected["is_winning_status"]]
        detectors = set()
        rules = set()
        languages = set()
        for value in part["detectors"]:
            detectors.update(_safe_json_list(value))
        for value in part["rules"]:
            rules.update(_safe_json_list(value))
        for value in part["languages"]:
            languages.update(_safe_json_list(value))
        rows.append({
            "phenotype": phenotype,
            "propositions": len(part),
            "unique_studies": part["StudyInstanceUID"].nunique(),
            "selected_pair_participations": selected[["StudyInstanceUID", "target"]].drop_duplicates().shape[0],
            "selected_winning_pair_participations": winning[["StudyInstanceUID", "target"]].drop_duplicates().shape[0],
            "targets": _json_list(part["target"]),
            "statuses": _json_list(part["status"]),
            "detectors": _json_list(detectors),
            "languages": _json_list(languages),
            "rules": _json_list(rules),
        })
    phenotype_summary = pd.DataFrame(rows).sort_values("propositions", ascending=False)

    detail_rows = []
    totals = propositions.groupby(["target", "status"]).size()
    for (target, phenotype, status), part in propositions.groupby(["target", "phenotype", "status"], sort=True):
        selected = evidence[
            evidence["target"].eq(target)
            & evidence["phenotype"].eq(phenotype)
            & evidence["proposition_status"].eq(status)
        ]
        denominator = int(totals.loc[(target, status)])
        detail_rows.append({
            "target": target,
            "phenotype": phenotype,
            "status": status,
            "propositions": len(part),
            "proportion_within_target_status_propositions": len(part) / denominator,
            "target_status_proposition_denominator": denominator,
            "selected_winning_evidence_instances": int(selected["is_winning_status"].sum()),
        })
    return phenotype_summary, pd.DataFrame(detail_rows)


def rule_summary(
    mentions: pd.DataFrame,
    propositions: pd.DataFrame,
    evidence: pd.DataFrame,
) -> pd.DataFrame:
    rules = set(mentions["rule"])
    for value in propositions["rules"]:
        rules.update(_safe_json_list(value) or ["<no_explicit_rule>"])
    for value in evidence["rules"]:
        rules.update(_safe_json_list(value) or ["<no_explicit_rule>"])
    rows = []
    for rule in sorted(rules):
        mention_part = mentions[mentions["rule"].eq(rule)]
        prop_mask = propositions["rules"].map(
            lambda value: rule in (_safe_json_list(value) or ["<no_explicit_rule>"])
        )
        prop_part = propositions[prop_mask]
        selected_mask = evidence["rules"].map(
            lambda value: rule in (_safe_json_list(value) or ["<no_explicit_rule>"])
        )
        selected = evidence[selected_mask]
        winning = selected[selected["is_winning_status"]]
        detector_values = set(mention_part["detector"])
        for value in prop_part["detectors"]:
            detector_values.update(_safe_json_list(value))
        language_values = set(mention_part["language"])
        for value in prop_part["languages"]:
            language_values.update(_safe_json_list(value))
        rows.append({
            "rule": rule,
            "is_explicit_rule": rule != "<no_explicit_rule>",
            "mentions": len(mention_part),
            "propositions": len(prop_part),
            "unique_studies": prop_part["StudyInstanceUID"].nunique(),
            "selected_pair_participations": selected[["StudyInstanceUID", "target"]].drop_duplicates().shape[0],
            "selected_winning_pair_participations": winning[["StudyInstanceUID", "target"]].drop_duplicates().shape[0],
            "detectors": _json_list(detector_values),
            "targets": _json_list(prop_part["target"]),
            "languages": _json_list(language_values),
            "phenotypes": _json_list(prop_part["phenotype"]),
            "statuses": _json_list(prop_part["status"]),
        })
    output = pd.DataFrame(rows).sort_values(
        ["selected_winning_pair_participations", "propositions", "rule"],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    total = output["selected_winning_pair_participations"].sum()
    output["cumulative_selected_participation_share"] = (
        output["selected_winning_pair_participations"].cumsum() / total if total else np.nan
    )
    output["cumulative_note"] = "Participation denominator; pairs may participate through multiple rules."
    return output


def duplicate_tables(
    reports: pd.DataFrame,
    views: pd.DataFrame,
    evidence: pd.DataFrame,
    text_limit: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    levels = {
        "Report": reports.assign(instance_id=reports["StudyInstanceUID"], text=reports["Report"])[
            ["instance_id", "StudyInstanceUID", "text", "normalized_text"]
        ],
        "strict TextView": views[views["view_kind"].eq("strict")].rename(columns={"view_id": "instance_id"})[
            ["instance_id", "StudyInstanceUID", "text", "normalized_text"]
        ],
        "linked TextView": views[views["view_kind"].eq("linked")].rename(columns={"view_id": "instance_id"})[
            ["instance_id", "StudyInstanceUID", "text", "normalized_text"]
        ],
        "selected evidence": evidence.assign(
            instance_id=lambda frame: frame["StudyInstanceUID"].astype(str)
            + ":" + frame["target"].astype(str)
            + ":" + frame["selected_order"].astype(str)
        ).rename(columns={"evidence": "text", "normalized_evidence": "normalized_text"})[
            ["instance_id", "StudyInstanceUID", "text", "normalized_text"]
        ],
    }
    summary_rows = []
    distribution_rows = []
    group_rows = []
    for level, frame in levels.items():
        sizes = frame.groupby("normalized_text", dropna=False).size()
        duplicate_sizes = sizes[sizes > 1]
        total = len(frame)
        unique = sizes.size
        duplicated_instances = total - unique
        summary_rows.append({
            "level": level,
            "total_instances": total,
            "unique_texts": unique,
            "duplicated_instances_excess": duplicated_instances,
            "duplicate_rate_excess": duplicated_instances / total if total else np.nan,
            "instances_in_duplicate_groups": int(duplicate_sizes.sum()),
            "duplicate_groups": len(duplicate_sizes),
            "mean_duplicate_group_size": duplicate_sizes.mean() if len(duplicate_sizes) else np.nan,
            "median_duplicate_group_size": duplicate_sizes.median() if len(duplicate_sizes) else np.nan,
            "max_duplicate_group_size": int(duplicate_sizes.max()) if len(duplicate_sizes) else 0,
            "duplicate_definition": "excess instances = total instances - unique normalized texts",
        })
        for size, count in duplicate_sizes.value_counts().sort_index().items():
            distribution_rows.append({
                "level": level,
                "group_size": int(size),
                "groups": int(count),
                "instances": int(size * count),
            })
        duplicate_texts = set(duplicate_sizes.index)
        for normalized, part in frame[frame["normalized_text"].isin(duplicate_texts)].groupby("normalized_text", sort=False):
            group_rows.append({
                "level": level,
                "group_sha256": _group_hash(level, str(normalized)),
                "group_size": len(part),
                "unique_studies": part["StudyInstanceUID"].nunique(),
                "normalized_text": str(normalized)[:text_limit],
                "example_text": str(part["text"].iloc[0])[:text_limit],
                "instance_ids": _json(list(part["instance_id"].astype(str))),
                "StudyInstanceUIDs": _json(sorted(part["StudyInstanceUID"].astype(str).unique().tolist())),
            })
    return (
        pd.DataFrame(summary_rows),
        pd.DataFrame(distribution_rows),
        pd.DataFrame(group_rows).sort_values(["group_size", "level"], ascending=[False, True]),
    )


def template_family_tables(
    reports: pd.DataFrame,
    supervision: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reuse v3 exact/numeric normalization while retaining singleton families."""
    base = reports[["StudyInstanceUID", "normalized_text", "language_group"]].copy()
    base["exact"] = base["normalized_text"]
    base["numeric_normalized"] = base["normalized_text"].map(
        lambda value: NUMBER_PATTERN.sub("<num>", value)
    )
    map_rows = []
    family_rows = []
    for mode in ("exact", "numeric_normalized"):
        base[f"{mode}_family"] = base[mode].map(lambda text: _group_hash(mode, text))
        map_rows.extend({
            "StudyInstanceUID": row.StudyInstanceUID,
            "template_mode": mode,
            "template_family_sha256": getattr(row, f"{mode}_family"),
        } for row in base.itertuples(index=False))
        for family, members in base.groupby(f"{mode}_family", sort=True):
            uids = sorted(members["StudyInstanceUID"].astype(str).tolist())
            statuses = supervision[supervision["StudyInstanceUID"].isin(uids)]
            target_status_counts = {
                target: {str(status): int(count) for status, count in part["status"].value_counts().sort_index().items()}
                for target, part in statuses.groupby("target", sort=True)
            }
            inconsistent_targets = [
                target for target, values in target_status_counts.items() if len(values) > 1
            ]
            family_rows.append({
                "template_mode": mode,
                "template_family_sha256": family,
                "reports": len(members),
                "is_duplicated_family": len(members) > 1,
                "StudyInstanceUIDs": _json(uids),
                "languages": _json_list(members["language_group"]),
                "target_status_counts": _json(target_status_counts),
                "homogeneous_across_each_target": len(inconsistent_targets) == 0,
                "heterogeneous_target_count": len(inconsistent_targets),
                "heterogeneous_targets": _json(inconsistent_targets),
            })
    maps = pd.DataFrame(map_rows).pivot(
        index="StudyInstanceUID", columns="template_mode", values="template_family_sha256",
    ).reset_index().rename_axis(columns=None).rename(columns={
        "exact": "exact_template_family",
        "numeric_normalized": "numeric_normalized_template_family",
    })
    return pd.DataFrame(family_rows), maps


def _ngram_counter(texts: Iterable[str], order: int) -> Counter[str]:
    counter: Counter[str] = Counter()
    for text in texts:
        tokens = simple_tokens(text)
        if order == 1:
            counter.update(tokens)
        else:
            counter.update(" ".join(tokens[index:index + order]) for index in range(len(tokens) - order + 1))
    return counter


def lexical_tables(
    evidence: pd.DataFrame,
    top_k: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    winning = evidence[evidence["is_winning_status"]].copy()
    summary_rows = []
    ngram_rows = []
    evidence_rows = []
    for (target, status), part in winning.groupby(["target", "proposition_status"], sort=True):
        normalized = part["normalized_evidence"]
        tokens = [token for text in normalized for token in simple_tokens(text)]
        unigram = _ngram_counter(normalized, 1)
        bigram = _ngram_counter(normalized, 2)
        record = {
            "target": target,
            "status": status,
            "evidence_instances": len(part),
            "unique_normalized_texts": normalized.nunique(),
            "duplicated_instances_excess": len(part) - normalized.nunique(),
            "duplicate_rate_excess": (len(part) - normalized.nunique()) / len(part),
            "total_simple_tokens": len(tokens),
            "unique_tokens": len(set(tokens)),
            "type_token_ratio": len(set(tokens)) / len(tokens) if tokens else np.nan,
            "ttr_note": "Type-token ratio depends on the number of observed tokens.",
        }
        for order_name, counter in (("unigram", unigram), ("bigram", bigram)):
            total = sum(counter.values())
            for n in (10, 25, 50, 100):
                available_n = min(n, len(counter))
                covered = sum(value for _, value in counter.most_common(available_n))
                record[f"{order_name}_top_{n}_coverage"] = covered / total if total else np.nan
                record[f"{order_name}_top_{n}_actual_n"] = available_n
            cumulative = 0
            for rank, (ngram, count) in enumerate(counter.most_common(top_k), start=1):
                cumulative += count
                ngram_rows.append({
                    "target": target,
                    "status": status,
                    "ngram_order": 1 if order_name == "unigram" else 2,
                    "rank": rank,
                    "ngram": ngram,
                    "count": count,
                    "share": count / total if total else np.nan,
                    "cumulative_share": cumulative / total if total else np.nan,
                    "total_ngram_occurrences": total,
                })
        summary_rows.append(record)

        detectors = set()
        phenotypes = set(part["phenotype"])
        rules = set()
        languages = set(part["report_language_group"])
        for value in part["detectors"]:
            detectors.update(_safe_json_list(value))
        for value in part["rules"]:
            rules.update(_safe_json_list(value))
        evidence_rows.append({
            "target": target,
            "status": status,
            "evidence_instances": len(part),
            "unique_normalized_evidence": normalized.nunique(),
            "proportion_duplicated_excess": (len(part) - normalized.nunique()) / len(part),
            "detectors": _json_list(detectors),
            "phenotypes": _json_list(phenotypes),
            "rules": _json_list(rules),
            "languages": _json_list(languages),
        })
    return pd.DataFrame(summary_rows), pd.DataFrame(ngram_rows), pd.DataFrame(evidence_rows)


def _sample_pair_indices(count: int, maximum: int, seed: int) -> list[tuple[int, int]]:
    possible = count * (count - 1) // 2
    if possible <= maximum:
        return list(itertools.combinations(range(count), 2))
    rng = random.Random(seed)
    selected: set[tuple[int, int]] = set()
    while len(selected) < maximum:
        first, second = rng.sample(range(count), 2)
        selected.add((min(first, second), max(first, second)))
    return sorted(selected)


def text_similarity_summary(
    evidence: pd.DataFrame,
    parameters: InspectionParameters,
) -> pd.DataFrame:
    """Describe pairwise textual similarity using exact and token Jaccard only."""
    winning = evidence[evidence["is_winning_status"]].copy()
    rows = []
    for (target, status), part in winning.groupby(["target", "proposition_status"], sort=True):
        texts = part["evidence"].astype(str).tolist()
        normalized = part["normalized_evidence"].astype(str).tolist()
        token_sets = [set(simple_tokens(text)) for text in normalized]
        pair_indices = _sample_pair_indices(
            len(texts), parameters.similarity_max_pairs_per_stratum,
            int(_stable_hash(parameters.seed, target, status)[:12], 16),
        ) if len(texts) >= 2 else []
        jaccard = []
        exact = 0
        normalized_exact = 0
        for first, second in pair_indices:
            exact += texts[first] == texts[second]
            normalized_exact += normalized[first] == normalized[second]
            union = token_sets[first] | token_sets[second]
            intersection = token_sets[first] & token_sets[second]
            jaccard.append(len(intersection) / len(union) if union else 1.0)
        stats = _describe(pd.Series(jaccard, dtype=float))
        rows.append({
            "target": target,
            "status": status,
            "evidence_instances": len(texts),
            "possible_pairs": len(texts) * (len(texts) - 1) // 2,
            "evaluated_pairs": len(pair_indices),
            "pair_sampling": "all" if len(pair_indices) == len(texts) * (len(texts) - 1) // 2 else "deterministic_sample",
            "raw_exact_match_rate": exact / len(pair_indices) if pair_indices else np.nan,
            "normalized_exact_match_rate": normalized_exact / len(pair_indices) if pair_indices else np.nan,
            **{f"jaccard_{key}": value for key, value in stats.items() if key != "count"},
            "method": "Jaccard over sets of normalize_text + Unicode simple_tokens; no embeddings or external model",
        })
    return pd.DataFrame(rows)


def conflict_cases(supervision: pd.DataFrame, evidence: pd.DataFrame) -> pd.DataFrame:
    conflict_pairs = supervision[supervision["rationale"].str.contains("conflict", regex=False)][
        ["StudyInstanceUID", "target", "status", "confidence", "rationale", "language_group", "evidence_provenance"]
    ].copy()
    if conflict_pairs.empty:
        return pd.DataFrame(columns=[
            "StudyInstanceUID", "target", "winning_status", "conflicting_statuses",
            "confidence", "language_group", "detectors", "phenotypes", "rules",
            "rationale", "evidence_provenance",
        ])
    rows = []
    for row in conflict_pairs.itertuples(index=False):
        part = evidence[
            evidence["StudyInstanceUID"].eq(row.StudyInstanceUID)
            & evidence["target"].eq(row.target)
        ]
        detectors = set()
        rules = set()
        for value in part["detectors"]:
            detectors.update(_safe_json_list(value))
        for value in part["rules"]:
            rules.update(_safe_json_list(value))
        rows.append({
            "StudyInstanceUID": row.StudyInstanceUID,
            "target": row.target,
            "winning_status": row.status,
            "conflicting_statuses": _json_list(part.loc[~part["is_winning_status"], "proposition_status"]),
            "confidence": row.confidence,
            "language_group": row.language_group,
            "detectors": _json_list(detectors),
            "phenotypes": _json_list(part["phenotype"]),
            "rules": _json_list(rules),
            "rationale": row.rationale,
            "evidence_provenance": row.evidence_provenance,
        })
    return pd.DataFrame(rows)


def collective_evidence_summary(
    mentions: pd.DataFrame,
    propositions: pd.DataFrame,
    evidence: pd.DataFrame,
) -> pd.DataFrame:
    collective_props = propositions[propositions["collective"]]
    rows = []
    groups = ["target", "status", "rule_combination", "language_combination", "phenotype", "confidence"]
    collective_mentions = mentions[mentions["collective"]].copy()
    mention_groups = ["target", "status", "rule", "language", "phenotype", "confidence"]
    for key, part in collective_mentions.groupby(mention_groups, dropna=False, sort=True):
        rows.append({
            "record_type": "mention",
            "target": key[0],
            "status": key[1],
            "rule_combination": key[2],
            "language_combination": key[3],
            "phenotype": key[4],
            "confidence": key[5],
            "mentions": len(part),
            "propositions": 0,
            "unique_studies": part["StudyInstanceUID"].nunique(),
            "selected_propositions": 0,
            "selected_winning_propositions": 0,
            "selected_study_target_pairs": 0,
        })
    for key, part in collective_props.groupby(groups, dropna=False, sort=True):
        selected = evidence[
            evidence["collective"]
            & evidence["target"].eq(key[0])
            & evidence["proposition_status"].eq(key[1])
            & evidence["rule_combination"].eq(key[2])
            & evidence["language_combination"].eq(key[3])
            & evidence["phenotype"].eq(key[4])
            & evidence["proposition_confidence"].eq(key[5])
        ]
        rows.append({
            "record_type": "proposition",
            **dict(zip(groups, key)),
            "mentions": 0,
            "propositions": len(part),
            "unique_studies": part["StudyInstanceUID"].nunique(),
            "selected_propositions": len(selected),
            "selected_winning_propositions": int(selected["is_winning_status"].sum()),
            "selected_study_target_pairs": selected[["StudyInstanceUID", "target"]].drop_duplicates().shape[0],
        })
    return pd.DataFrame(rows)


def view_tables(
    views: pd.DataFrame,
    mentions: pd.DataFrame,
    propositions: pd.DataFrame,
    evidence: pd.DataFrame,
    reports: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows = []
    for view_kind in ("strict", "linked"):
        rows.append({
            "record_type": "overall",
            "view_kind": view_kind,
            "support_scope": "__all__",
            "target": "__all__",
            "status": "__all__",
            "detector": "__all__",
            "rule": "__all__",
            "phenotype": "__all__",
            "views": int(views["view_kind"].eq(view_kind).sum()),
            "mentions": int(mentions["view_kind"].eq(view_kind).sum()),
            "propositions": int(propositions["view_kinds"].map(lambda value: view_kind in _safe_json_list(value)).sum()),
            "selected_pair_participations": evidence[
                evidence["views"].map(lambda value: view_kind in _safe_json_list(value))
            ][["StudyInstanceUID", "target"]].drop_duplicates().shape[0],
        })
    for support_scope, part in propositions.groupby("view_support", sort=True):
        rows.append({
            "record_type": "proposition_support_scope",
            "view_kind": "__all__",
            "support_scope": support_scope,
            "target": "__all__",
            "status": "__all__",
            "detector": "__all__",
            "rule": "__all__",
            "phenotype": "__all__",
            "views": np.nan,
            "mentions": np.nan,
            "propositions": len(part),
            "selected_pair_participations": evidence[evidence["view_support"].eq(support_scope)][
                ["StudyInstanceUID", "target"]
            ].drop_duplicates().shape[0],
        })
    detail_rows = []
    for prop in propositions.itertuples(index=False):
        for detector in _safe_json_list(prop.detectors):
            for rule in (_safe_json_list(prop.rules) or ["<no_explicit_rule>"]):
                detail_rows.append({
                    "view_kind": prop.view_support,
                    "target": prop.target,
                    "status": prop.status,
                    "detector": detector,
                    "rule": rule,
                    "phenotype": prop.phenotype,
                    "proposition_id": prop.proposition_id,
                    "StudyInstanceUID": prop.StudyInstanceUID,
                })
    detail = pd.DataFrame(detail_rows)
    if not detail.empty:
        for key, part in detail.groupby(["view_kind", "target", "status", "detector", "rule", "phenotype"], sort=True):
            rows.append({
                "record_type": "detail",
                "view_kind": key[0],
                "support_scope": key[0],
                "target": key[1],
                "status": key[2],
                "detector": key[3],
                "rule": key[4],
                "phenotype": key[5],
                "views": np.nan,
                "mentions": np.nan,
                "propositions": part["proposition_id"].nunique(),
                "selected_pair_participations": np.nan,
            })

    winning = evidence[evidence["is_winning_status"]].copy()
    linked_pairs = winning.groupby(["StudyInstanceUID", "target"], sort=False)["view_support"].agg(list).reset_index()
    linked_pairs["dependency_type"] = linked_pairs["view_support"].map(
        lambda values: "linked_only" if all(value == "linked_only" for value in values)
        else "includes_linked_and_strict" if any("linked" in value for value in values)
        else "strict_only"
    )
    linked_pairs = linked_pairs[linked_pairs["dependency_type"].ne("strict_only")]
    linked_cases = linked_pairs.merge(
        winning.drop(columns=["view_support"]), on=["StudyInstanceUID", "target"], validate="one_to_many",
    ).merge(
        reports[["StudyInstanceUID", "Report"]], on="StudyInstanceUID", validate="many_to_one",
    )

    context = evidence.copy()
    context["context_structure"] = np.select(
        [context["collective"], context["source_clause_count"].eq(1), context["source_clause_count"].eq(2)],
        ["collective", "single_clause", "linked_two_clauses"],
        default="other",
    )
    context_rows = []
    for key, part in context.groupby(
        ["context_structure", "target", "proposition_status", "detector_combination", "phenotype", "rule_combination"],
        sort=True,
    ):
        context_rows.append({
            "context_structure": key[0],
            "target": key[1],
            "status": key[2],
            "detector": key[3],
            "phenotype": key[4],
            "rule": key[5],
            "selected_evidence_instances": len(part),
            "unique_study_target_pairs": part[["StudyInstanceUID", "target"]].drop_duplicates().shape[0],
        })
    return pd.DataFrame(rows), linked_cases, pd.DataFrame(context_rows)


def _negation_type(row: object) -> str:
    text = str(row.evidence)
    spans = _safe_json_list(row.spans)
    finding_spans = [tuple(int(value) for value in span) for span in spans if isinstance(span, list) and len(span) == 2]
    negations = matching_terms(text, NEGATION_TERMS)
    for start, end, term in negations:
        if any(end <= finding_start and finding_start - end <= 90 for finding_start, _ in finding_spans):
            return "preposed"
        if term in POSTPOSED_NEGATION_TERMS and any(
            start >= finding_end and start - finding_end <= 40 for _, finding_end in finding_spans
        ):
            return "postposed"
    if any(term in normalize_text(text) for term in NORMALITY_TERMS):
        return "explicit_normality"
    if negations:
        return "other_implemented_negation"
    return "negative_status_without_reconstructed_marker"


def negation_summary(evidence: pd.DataFrame) -> pd.DataFrame:
    negative = evidence[
        evidence["is_winning_status"] & evidence["proposition_status"].eq("negative")
    ].copy()
    negative["negation_type"] = [_negation_type(row) for row in negative.itertuples(index=False)]
    rows = []
    groups = [
        "negation_type", "target", "report_language_group", "detector_combination",
        "rule_combination", "phenotype",
    ]
    for key, part in negative.groupby(groups, sort=True):
        rows.append({
            **dict(zip(groups, key)),
            "evidence_instances": len(part),
            "unique_evidence_texts": part["normalized_evidence"].nunique(),
            "unique_studies": part["StudyInstanceUID"].nunique(),
            "example_evidence": part.sort_values(["StudyInstanceUID", "target"])["evidence"].iloc[0],
            "classification_basis": "existing NEGATION_TERMS, POSTPOSED_NEGATION_TERMS, NORMALITY_TERMS and stored spans",
        })
    return pd.DataFrame(rows)


def _uncertainty_patterns(text: str) -> list[str]:
    patterns = [match.group(0) for match in _V3_UNCERTAINTY.finditer(text)]
    patterns.extend(term for _, _, term in matching_terms(text, UNCERTAINTY_TERMS))
    return sorted(set(patterns)) or ["<uncertain_status_without_reconstructed_marker>"]


def uncertain_summary(evidence: pd.DataFrame) -> pd.DataFrame:
    uncertain = evidence[
        evidence["is_winning_status"] & evidence["proposition_status"].eq("uncertain")
    ].copy()
    rows = []
    for item in uncertain.itertuples(index=False):
        for pattern in _uncertainty_patterns(item.evidence):
            rows.append({
                "StudyInstanceUID": item.StudyInstanceUID,
                "target": item.target,
                "language_group": item.report_language_group,
                "detector": item.detector_combination,
                "rule": item.rule_combination,
                "phenotype": item.phenotype,
                "uncertainty_pattern": pattern,
                "evidence": item.evidence,
                "normalized_evidence": item.normalized_evidence,
            })
    detail = pd.DataFrame(rows)
    if detail.empty:
        return pd.DataFrame(columns=[
            "target", "language_group", "detector", "rule", "phenotype",
            "uncertainty_pattern", "evidence_instances", "unique_evidence_texts",
            "duplicate_rate_excess", "example_evidence",
        ])
    outputs = []
    group = ["target", "language_group", "detector", "rule", "phenotype", "uncertainty_pattern"]
    for key, part in detail.groupby(group, sort=True):
        unique = part["normalized_evidence"].nunique()
        outputs.append({
            **dict(zip(group, key)),
            "evidence_instances": len(part),
            "unique_evidence_texts": unique,
            "duplicate_rate_excess": (len(part) - unique) / len(part),
            "example_evidence": part.sort_values("StudyInstanceUID")["evidence"].iloc[0],
        })
    return pd.DataFrame(outputs)


def unknown_summary(
    supervision: pd.DataFrame,
    reports: pd.DataFrame,
) -> pd.DataFrame:
    report_fields = reports[[
        "StudyInstanceUID", "characters", "simple_tokens", "clauses", "strict_views", "linked_views",
    ]]
    working = supervision.merge(report_fields, on="StudyInstanceUID", validate="many_to_one")
    resolved_by_study = supervision["status"].isin(BINARY_STATUSES).groupby(supervision["StudyInstanceUID"]).sum()
    working["other_binary_resolved_targets"] = working["StudyInstanceUID"].map(resolved_by_study) - working["status"].isin(BINARY_STATUSES).astype(int)
    rows = []
    for (target, language), all_pairs in working.groupby(["target", "language_group"], sort=True):
        part = all_pairs[all_pairs["status"].eq("unknown")]
        rows.append({
            "target": target,
            "language_group": language,
            "pairs": len(all_pairs),
            "unknown": len(part),
            "unknown_rate": len(part) / len(all_pairs),
            "mean_report_characters": part["characters"].mean() if len(part) else np.nan,
            "mean_report_simple_tokens": part["simple_tokens"].mean() if len(part) else np.nan,
            "mean_clauses": part["clauses"].mean() if len(part) else np.nan,
            "median_clauses": part["clauses"].median() if len(part) else np.nan,
            "mean_strict_views": part["strict_views"].mean() if len(part) else np.nan,
            "mean_linked_views": part["linked_views"].mean() if len(part) else np.nan,
            "reports_with_other_binary_resolved_target": int(part["other_binary_resolved_targets"].gt(0).sum()),
            "mean_other_binary_resolved_targets": part["other_binary_resolved_targets"].mean() if len(part) else np.nan,
            "interpretation_limit": "Observable structure only; unknown is not interpreted as clinically irrelevant.",
        })
    return pd.DataFrame(rows)


def clause_usage_summary(
    views: pd.DataFrame,
    mentions: pd.DataFrame,
    evidence: pd.DataFrame,
) -> pd.DataFrame:
    strict = views[views["view_kind"].eq("strict") & views["diagnostic"]].copy()
    selected_keys = set(zip(evidence["StudyInstanceUID"], evidence["normalized_evidence"]))
    mention_keys = set(zip(mentions["StudyInstanceUID"], mentions["normalized_text"]))
    strict["selected_for_any_target"] = [
        (uid, text) in selected_keys for uid, text in zip(strict["StudyInstanceUID"], strict["normalized_text"])
    ]
    strict["contains_detector_mention"] = [
        (uid, text) in mention_keys for uid, text in zip(strict["StudyInstanceUID"], strict["normalized_text"])
    ]
    strict["usage_category"] = np.select(
        [strict["selected_for_any_target"], strict["contains_detector_mention"]],
        ["selected_evidence_for_at_least_one_target", "not_selected_but_contains_detector_mention"],
        default="no_detector_mention",
    )
    rows = []
    for category, part in strict.groupby("usage_category", sort=True):
        rows.append({
            "usage_category": category,
            "diagnostic_strict_clauses": len(part),
            "unique_normalized_texts": part["normalized_text"].nunique(),
            "unique_studies": part["StudyInstanceUID"].nunique(),
            "mean_characters": part["characters"].mean(),
            "mean_simple_tokens": part["simple_tokens"].mean(),
            "semantic_label_created": False,
        })
    return pd.DataFrame(rows)


def study_level_distribution(
    supervision: pd.DataFrame,
    propositions: pd.DataFrame,
    evidence: pd.DataFrame,
) -> pd.DataFrame:
    status_counts = supervision.pivot_table(
        index="StudyInstanceUID", columns="status", values="target", aggfunc="count", fill_value=0,
    ).reindex(columns=VALID_STATUSES, fill_value=0)
    status_counts.columns = [f"{value}_targets" for value in status_counts.columns]
    status_counts["binary_resolved_targets"] = status_counts["positive_targets"] + status_counts["negative_targets"]
    proposition_counts = propositions.groupby("StudyInstanceUID").size().rename("propositions")
    evidence_counts = evidence.groupby("StudyInstanceUID").agg(
        selected_evidence_instances=("evidence", "size"),
        unique_evidence_fragments=("normalized_evidence", "nunique"),
    )
    output = status_counts.join(proposition_counts, how="left").join(evidence_counts, how="left").fillna(0).reset_index()
    integer_columns = [column for column in output.columns if column != "StudyInstanceUID"]
    output[integer_columns] = output[integer_columns].astype(int)
    return output


def target_cooccurrence(
    supervision: pd.DataFrame,
    evidence: pd.DataFrame,
) -> pd.DataFrame:
    status_matrix = supervision.pivot(index="StudyInstanceUID", columns="target", values="status").reindex(columns=TARGETS)
    winning = evidence[evidence["is_winning_status"]]
    shared = winning.groupby(["StudyInstanceUID", "normalized_evidence"])["target"].agg(lambda values: sorted(set(values)))
    shared_pairs: Counter[tuple[str, str]] = Counter()
    for targets in shared:
        for first in targets:
            for second in targets:
                shared_pairs[(first, second)] += 1
    rows = []
    for matrix_type, mask in (
        ("positive_positive", status_matrix.eq("positive")),
        ("binary_resolved", status_matrix.isin(BINARY_STATUSES)),
    ):
        for first in TARGETS:
            for second in TARGETS:
                rows.append({
                    "matrix_type": matrix_type,
                    "row_target": first,
                    "column_target": second,
                    "study_count": int((mask[first] & mask[second]).sum()),
                    "denominator_studies": len(status_matrix),
                })
    for first in TARGETS:
        for second in TARGETS:
            rows.append({
                "matrix_type": "shared_normalized_selected_evidence",
                "row_target": first,
                "column_target": second,
                "study_count": shared_pairs[(first, second)],
                "denominator_studies": len(status_matrix),
            })
    return pd.DataFrame(rows)


def effective_example_structure(
    evidence: pd.DataFrame,
    template_map: pd.DataFrame,
) -> pd.DataFrame:
    winning = evidence[evidence["is_winning_status"]].merge(
        template_map, on="StudyInstanceUID", validate="many_to_one",
    )
    rows = []
    for (target, status), part in winning.groupby(["target", "proposition_status"], sort=True):
        detector_rules = set()
        languages = set(part["report_language_group"])
        for row in part.itertuples(index=False):
            detectors = _safe_json_list(row.detectors) or ["<none>"]
            rules = _safe_json_list(row.rules) or ["<no_explicit_rule>"]
            detector_rules.update(f"{detector}::{rule}" for detector in detectors for rule in rules)
        rows.append({
            "target": target,
            "status": status,
            "raw_evidence_count": len(part),
            "unique_normalized_evidence_count": part["normalized_evidence"].nunique(),
            "unique_report_count": part["StudyInstanceUID"].nunique(),
            "unique_exact_template_family_count": part["exact_template_family"].nunique(),
            "unique_numeric_normalized_template_family_count": part["numeric_normalized_template_family"].nunique(),
            "detector_rule_combination_count": len(detector_rules),
            "detector_rule_combinations": _json(sorted(detector_rules)),
            "language_group_count": len(languages),
            "language_groups": _json(sorted(languages)),
            "note": "No effective sample size is estimated; columns are structural counts.",
        })
    return pd.DataFrame(rows)


def audit_sample(
    supervision: pd.DataFrame,
    evidence: pd.DataFrame,
    reports: pd.DataFrame,
    parameters: InspectionParameters,
) -> pd.DataFrame:
    """Build deterministic, inspectable strata without adding correctness judgments."""
    report_text = reports[["StudyInstanceUID", "Report"]]
    resolved = evidence[evidence["is_winning_status"]].copy()
    resolved["stratum_id"] = (
        resolved["target"].astype(str) + "|" + resolved["proposition_status"].astype(str)
        + "|" + resolved["detector_combination"].astype(str)
        + "|" + resolved["rule_combination"].astype(str)
        + "|" + resolved["phenotype"].astype(str)
        + "|" + resolved["report_language_group"].astype(str)
        + "|" + resolved["has_conflict"].astype(str)
        + "|" + resolved["view_support"].astype(str)
        + "|" + resolved["collective"].astype(str)
    )
    resolved["sample_rank_hash"] = [
        _stable_hash(parameters.seed, row.stratum_id, row.StudyInstanceUID, row.target, row.evidence)
        for row in resolved.itertuples(index=False)
    ]
    resolved = resolved.sort_values("sample_rank_hash").drop_duplicates("stratum_id")
    resolved["sample_source"] = "selected_winning_evidence_stratum"

    unknown = supervision[supervision["status"].eq("unknown")][
        ["StudyInstanceUID", "target", "status", "language_group", "rationale", "evidence_provenance"]
    ].copy()
    unknown["stratum_id"] = unknown["target"].astype(str) + "|unknown|" + unknown["language_group"].astype(str)
    unknown["sample_rank_hash"] = [
        _stable_hash(parameters.seed, row.stratum_id, row.StudyInstanceUID)
        for row in unknown.itertuples(index=False)
    ]
    unknown = unknown.sort_values("sample_rank_hash").drop_duplicates("stratum_id")
    unknown_rows = pd.DataFrame({
        "StudyInstanceUID": unknown["StudyInstanceUID"],
        "target": unknown["target"],
        "final_status": "unknown",
        "proposition_status": "unknown",
        "evidence": "",
        "phenotype": "",
        "detector_combination": "",
        "rule_combination": "",
        "report_language_group": unknown["language_group"],
        "has_conflict": False,
        "view_support": "none",
        "collective": False,
        "rationale": unknown["rationale"],
        "stratum_id": unknown["stratum_id"],
        "sample_rank_hash": unknown["sample_rank_hash"],
        "sample_source": "unknown_target_language_stratum",
    })
    columns = [
        "StudyInstanceUID", "target", "final_status", "proposition_status", "evidence",
        "phenotype", "detector_combination", "rule_combination", "report_language_group",
        "has_conflict", "view_support", "collective", "rationale", "stratum_id",
        "sample_rank_hash", "sample_source",
    ]
    candidates = pd.concat([resolved[columns], unknown_rows[columns]], ignore_index=True)
    candidates = candidates.sort_values("sample_rank_hash").head(parameters.audit_sample_max_rows)
    candidates = candidates.merge(report_text, on="StudyInstanceUID", validate="many_to_one")
    candidates.insert(0, "sample_id", [f"audit-{index:04d}" for index in range(1, len(candidates) + 1)])
    candidates["seed"] = parameters.seed
    candidates["judgment"] = ""
    candidates["review_note"] = ""
    return candidates


def build_inspection_frames(
    train: pd.DataFrame,
    supervision: pd.DataFrame,
    parameters: InspectionParameters | None = None,
    expected_studies: int | None = None,
) -> tuple[dict[str, pd.DataFrame], dict[str, object]]:
    """Build every deterministic semantic artifact in memory."""
    parameters = parameters or InspectionParameters()
    train = train.copy()
    supervision = supervision.copy()
    train["StudyInstanceUID"] = train["StudyInstanceUID"].astype(str)
    supervision["StudyInstanceUID"] = supervision["StudyInstanceUID"].astype(str)
    validate_inspection_inputs(train, supervision, expected_studies or len(train))

    reports, views, mentions, propositions = reconstruct_runtime_units(train)
    evidence = build_evidence_inventory(supervision, reports)
    validate_runtime_reconciliation(supervision, reports, propositions, evidence)

    counts = corpus_unit_counts(reports, views, mentions, propositions, evidence, supervision)
    lengths = text_length_summary(reports, views, evidence)
    target_status = target_status_summary(supervision)
    languages, language_hypotheses_table, language_target = language_tables(
        reports, views, mentions, propositions, supervision,
    )
    detectors, detector_combinations = detector_tables(mentions, propositions, evidence)
    confidences = confidence_summary(supervision, evidence)
    phenotypes, target_phenotypes = phenotype_tables(propositions, evidence)
    rules = rule_summary(mentions, propositions, evidence)
    duplicate_summary_frame, duplicate_sizes, duplicate_groups = duplicate_tables(
        reports, views, evidence, parameters.duplicate_group_text_limit,
    )
    template_families, template_map = template_family_tables(reports, supervision)
    lexical, ngrams, evidence_target_status = lexical_tables(evidence, parameters.ngram_top_k)
    similarity = text_similarity_summary(evidence, parameters)
    conflicts = conflict_cases(supervision, evidence)
    collective = collective_evidence_summary(mentions, propositions, evidence)
    view_summary, linked_cases, context = view_tables(views, mentions, propositions, evidence, reports)
    negations = negation_summary(evidence)
    uncertain = uncertain_summary(evidence)
    unknown = unknown_summary(supervision, reports)
    clause_usage = clause_usage_summary(views, mentions, evidence)
    study_distribution = study_level_distribution(supervision, propositions, evidence)
    cooccurrence = target_cooccurrence(supervision, evidence)
    effective = effective_example_structure(evidence, template_map)
    sample = audit_sample(supervision, evidence, reports, parameters)

    existing_templates = exact_template_consistency(train, supervision)
    template_checks = {}
    for mode in ("exact", "numeric_normalized"):
        expected = int((existing_templates["template_mode"].eq(mode)).sum())
        observed = int(
            (template_families["template_mode"].eq(mode) & template_families["is_duplicated_family"]).sum()
        )
        if expected != observed:
            raise ValueError(f"{mode} duplicate template family count does not reconcile")
        template_checks[f"{mode}_duplicated_families"] = observed
    if int(existing_templates["inconsistent_targets"].sum()) != int(template_families["heterogeneous_target_count"].sum()):
        raise ValueError("template heterogeneity does not reconcile with v3 exact_template_consistency")

    frames = {
        "corpus_unit_counts": counts,
        "text_length_summary": lengths,
        "target_status_summary": target_status,
        "language_summary": languages,
        "language_hypothesis_summary": language_hypotheses_table,
        "language_target_status_summary": language_target,
        "detector_summary": detectors,
        "detector_combination_summary": detector_combinations,
        "confidence_summary": confidences,
        "phenotype_summary": phenotypes,
        "target_phenotype_status": target_phenotypes,
        "rule_summary": rules,
        "duplicate_summary": duplicate_summary_frame,
        "duplicate_group_size_distribution": duplicate_sizes,
        "duplicate_groups": duplicate_groups,
        "template_family_summary": template_families,
        "lexical_diversity_summary": lexical,
        "ngram_summary": ngrams,
        "text_similarity_summary": similarity,
        "evidence_target_status_summary": evidence_target_status,
        "evidence_inventory": evidence,
        "conflict_cases": conflicts,
        "collective_evidence_summary": collective,
        "view_kind_summary": view_summary,
        "linked_view_dependency_cases": linked_cases,
        "context_structure_summary": context,
        "negation_summary": negations,
        "uncertain_summary": uncertain,
        "unknown_summary": unknown,
        "clause_usage_summary": clause_usage,
        "study_level_distribution": study_distribution,
        "target_cooccurrence": cooccurrence,
        "effective_example_structure": effective,
        "audit_sample": sample,
    }
    diagnostics = {
        "studies": len(reports),
        "study_target_pairs": len(supervision),
        "strict_views": int(views["view_kind"].eq("strict").sum()),
        "linked_views": int(views["view_kind"].eq("linked").sum()),
        "mentions": len(mentions),
        "propositions": len(propositions),
        "selected_evidence_entries": len(evidence),
        "selected_winning_evidence_entries": int(evidence["is_winning_status"].sum()),
        "binary_resolved": int(supervision["status"].isin(BINARY_STATUSES).sum()),
        "status_counts": {status: int(supervision["status"].eq(status).sum()) for status in VALID_STATUSES},
        "template_checks": template_checks,
        "semantic_frame_count": len(frames),
    }
    return frames, diagnostics


def write_inspection_outputs(
    frames: dict[str, pd.DataFrame],
    output_dir: Path,
) -> dict[str, Path]:
    """Persist deterministic CSV artifacts using stage-03 line-ending conventions."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {key: output_dir / OUTPUT_FILES[key] for key in frames}
    for key, frame in frames.items():
        frame.to_csv(paths[key], index=False, lineterminator="\n")
    return paths


def build_run_metadata(
    *,
    train_path: Path,
    supervision_path: Path,
    policy_config_path: Path,
    reviewed_sources: Sequence[Path],
    output_paths: dict[str, Path],
    report_path: Path,
    frames: dict[str, pd.DataFrame],
    diagnostics: dict[str, object],
    parameters: InspectionParameters,
) -> dict[str, object]:
    """Create execution metadata after every semantic output and report exist."""
    source_paths = [train_path, supervision_path, policy_config_path, *reviewed_sources]
    return {
        "stage": "03_report_label_generation",
        "inspection_version": INSPECTION_VERSION,
        "policy_version": POLICY_VERSION,
        "execution_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "descriptive corpus and report-derived supervision inspection",
        "excluded_inputs": [
            "official_label values", "final_label overrides", "PixelData", "DICOM metadata",
            "Series metadata", "scanner", "anatomical plane", "external models", "embeddings",
        ],
        "inputs_and_reviewed_sources": [
            {"path": _portable_path(path.resolve()), "sha256": _sha256(path.resolve())}
            for path in source_paths
        ],
        "parameters": {
            **parameters.as_dict(),
            "simple_tokenization": "normalize_text followed by Unicode regex \\b\\w+\\b",
            "text_similarity": "raw exact, normalized exact, and token-set Jaccard",
            "template_modes": ["exact", "numeric_normalized"],
            "study_target_source": "status/derived_label/evidence_provenance; official/final values excluded",
        },
        "counts": diagnostics,
        "outputs": {
            **{
                key: {
                    "path": _portable_path(path.resolve()),
                    "sha256": _sha256(path.resolve()),
                    "rows": len(frames[key]),
                    "schema": {column: str(dtype) for column, dtype in frames[key].dtypes.items()},
                }
                for key, path in output_paths.items()
            },
            "report": {"path": _portable_path(report_path.resolve()), "sha256": _sha256(report_path.resolve())},
        },
        "reproducibility": (
            "CSV semantics are deterministic for fixed inputs, code, and parameters. "
            "Only execution_timestamp_utc and the metadata file hash vary by run."
        ),
    }


def run_inspection(
    *,
    train_path: Path,
    supervision_path: Path,
    policy_config_path: Path,
    output_dir: Path,
    report_path: Path,
    expected_studies: int,
    parameters: InspectionParameters | None = None,
    reviewed_sources: Sequence[Path] = (),
) -> dict[str, Path]:
    """Run the complete inspection and persist CSV, Markdown, and JSON outputs."""
    from .inspection_reporting import write_inspection_report

    parameters = parameters or InspectionParameters()
    train_path = train_path.resolve()
    supervision_path = supervision_path.resolve()
    policy_config_path = policy_config_path.resolve()
    output_dir = output_dir.resolve()
    report_path = report_path.resolve()
    config = json.loads(policy_config_path.read_text(encoding="utf-8"))
    if config.get("policy_version") != POLICY_VERSION:
        raise ValueError("policy configuration does not match executable v3")
    train = pd.read_csv(train_path, dtype={"StudyInstanceUID": str})
    required_supervision_columns = [
        "StudyInstanceUID", "report_sha256", "language_group", "target", "status",
        "derived_label", "confidence", "evidence", "rationale", "phenotypes",
        "detectors", "evidence_provenance", "policy_version",
    ]
    supervision = pd.read_csv(
        supervision_path,
        dtype={"StudyInstanceUID": str},
        usecols=required_supervision_columns,
        keep_default_na=False,
    )
    supervision["derived_label"] = pd.to_numeric(supervision["derived_label"], errors="coerce").astype("Int64")
    supervision["confidence"] = pd.to_numeric(supervision["confidence"], errors="raise")
    frames, diagnostics = build_inspection_frames(
        train, supervision, parameters=parameters, expected_studies=expected_studies,
    )
    output_paths = write_inspection_outputs(frames, output_dir)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    write_inspection_report(
        report_path, frames, diagnostics, parameters,
        train_path, supervision_path, policy_config_path, output_dir,
    )
    metadata = build_run_metadata(
        train_path=train_path,
        supervision_path=supervision_path,
        policy_config_path=policy_config_path,
        reviewed_sources=reviewed_sources,
        output_paths=output_paths,
        report_path=report_path,
        frames=frames,
        diagnostics=diagnostics,
        parameters=parameters,
    )
    metadata_path = output_dir / OUTPUT_FILES["metadata"]
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {**output_paths, "metadata": metadata_path, "report": report_path}
