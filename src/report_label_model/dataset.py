"""Auditable Stage 04 candidate construction and train-only deduplication."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Mapping

import pandas as pd

from src.report_labels.constants import ANATOMY_TERMS, DIRECT_TERMS, TARGETS
from src.report_labels.text import (
    _BOUNDARY,
    _join_wrapped_lines,
    contains_any,
    language_group,
    normalize_text,
    segment_report,
)
from src.report_labels.v3.extraction import V3ReportLabelExtractor
from src.report_labels.v3.inspection import NUMBER_PATTERN
from src.report_labels.v3.constants import DETECTOR_PRIORITY
from src.report_labels.v3.morphology import (
    DIRECT_RULES,
    OA_ANATOMY_PATTERNS,
    STRUCTURAL_ANATOMY_ROOTS,
)
from src.report_labels.v3.reconciliation import build_propositions

from .constants import TRUSTED_DETECTORS, TRUSTED_TEACHER_STATUSES, UPSTREAM_POLICY_VERSION


CANDIDATE_COLUMNS = [
    "example_id", "StudyInstanceUID", "source_index", "raw_clause",
    "normalized_clause", "normalized_clause_sha256", "target",
    "target_description", "label", "original_v3_status", "phenotype",
    "detectors", "detector_combination", "rules", "language_group",
    "view_kind", "collective", "conflict", "teacher_confidence",
    "evidence_provenance", "report_sha256", "exact_template_family",
    "numeric_normalized_template_family", "teacher_source_type",
    "no_evidence_source", "source_evidence_targets", "labeled_clause_targets",
    "no_evidence_guards", "alignment_verified",
]


@dataclass(frozen=True)
class SurfaceClause:
    source_index: int
    raw_clause: str
    normalized_clause: str
    section: str
    diagnostic: bool
    aligned: bool
    failure_reason: str = ""


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _json(values: object) -> str:
    return json.dumps(values, ensure_ascii=False, sort_keys=True)


def _json_list(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    if value is None or (isinstance(value, float) and pd.isna(value)) or value == "":
        return []
    parsed = json.loads(str(value))
    if not isinstance(parsed, list):
        raise ValueError("expected a JSON list")
    return parsed


def _stable_hash(seed: int, *values: object) -> str:
    payload = "|".join([str(seed), *(str(value) for value in values)])
    return _sha256_text(payload)


def minimal_model_text(value: object) -> str:
    """Normalize whitespace only; preserve case, accents and punctuation."""
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value).strip()


def _v3_structural_normalize(value: str) -> str:
    """Apply only the two documented structural rewrites in segment_report."""
    normalized = normalize_text(value)
    normalized = re.sub(
        r"\b([ivx]+)\.\s+(?=(?:stupnja|stepena|grad)\b)", r"\1 ", normalized,
    )
    normalized = re.sub(
        r"\b((?:deep|superficial)\s+)?(acl|pcl|mcl|lcl)\s*;\s*"
        r"(?=(?:high|low|grade|partial|complete|intact|normal|tear|sprain))",
        r"\1\2: ",
        normalized,
    )
    return normalized


def align_surface_clauses(report: object) -> list[SurfaceClause]:
    """Align current v3 strict clauses to surface fragments without fuzzy matching.

    V3 segments a normalized representation.  The raw fragments below use the
    same boundary and wrapped-line rules, then require exact normalization
    equality.  Structural v3 rewrites therefore become explicit failures.
    """
    expected = segment_report(report)
    if not isinstance(report, str) or not expected:
        return []
    joined = _join_wrapped_lines(report)
    raw_fragments = [part.strip(" -\t") for part in _BOUNDARY.split(joined) if part.strip()]
    output: list[SurfaceClause] = []
    raw_index = 0
    for source_index, clause in enumerate(expected):
        candidates: list[tuple[str, int]] = []
        # Multiple South-Slavic ordinal grades may occur in one semantic v3
        # clause.  Bound the exact reconstruction to six adjacent fragments.
        for consumed in range(1, min(6, len(raw_fragments) - raw_index) + 1):
            candidates.append((" ".join(raw_fragments[raw_index:raw_index + consumed]), consumed))
        match = next(
            ((raw, consumed) for raw, consumed in candidates if normalize_text(raw) == clause.text),
            None,
        )
        if match is None:
            # Recover sequence position only through the exact structural
            # rewrites already used by v3.  The clause remains an alignment
            # failure because normalize(raw_clause) itself is not equal.
            structural_match = next(
                ((raw, consumed) for raw, consumed in reversed(candidates)
                 if _v3_structural_normalize(raw) == clause.text),
                None,
            )
            if structural_match is None:
                raw = raw_fragments[raw_index] if raw_index < len(raw_fragments) else ""
                consumed = 1 if raw_index < len(raw_fragments) else 0
                reason = "exact_normalization_mismatch"
            else:
                raw, consumed = structural_match
                reason = "v3_structural_rewrite_not_surface_equivalent"
            output.append(SurfaceClause(
                source_index=source_index,
                raw_clause=minimal_model_text(raw),
                normalized_clause=clause.text,
                section=clause.section,
                diagnostic=clause.diagnostic,
                aligned=False,
                failure_reason=reason,
            ))
        else:
            raw, consumed = match
            output.append(SurfaceClause(
                source_index=source_index,
                raw_clause=minimal_model_text(raw),
                normalized_clause=clause.text,
                section=clause.section,
                diagnostic=clause.diagnostic,
                aligned=True,
            ))
        raw_index += consumed
    return output


def build_template_map(reports: pd.DataFrame) -> pd.DataFrame:
    """Reproduce Stage 03 exact/numeric-normalized report families."""
    required = {"StudyInstanceUID", "Report"}
    if missing := required - set(reports.columns):
        raise ValueError(f"reports missing columns: {sorted(missing)}")
    output = reports[["StudyInstanceUID", "Report"]].copy()
    output["StudyInstanceUID"] = output["StudyInstanceUID"].astype(str)
    output["normalized_report"] = output["Report"].map(normalize_text)
    output["exact_template_family"] = output["normalized_report"].map(
        lambda value: _sha256_text(f"exact:{value}")
    )
    output["numeric_normalized_template_family"] = output["normalized_report"].map(
        lambda value: _sha256_text(f"numeric_normalized:{NUMBER_PATTERN.sub('<num>', value)}")
    )
    output["report_sha256"] = output["normalized_report"].map(_sha256_text)
    return output


def identify_official_studies(supervision_path: Path) -> set[str]:
    """Read only the source indicator required to exclude gold Studies."""
    source = pd.read_csv(
        supervision_path,
        usecols=["StudyInstanceUID", "final_source"],
        dtype={"StudyInstanceUID": str, "final_source": str},
    )
    return set(source.loc[source["final_source"].eq("official"), "StudyInstanceUID"])


def _runtime_guards(
    reports: pd.DataFrame,
) -> tuple[
    dict[tuple[str, int], SurfaceClause],
    set[tuple[str, int, str]],
    set[tuple[str, int, str]],
    pd.DataFrame,
    pd.DataFrame,
]:
    extractor = V3ReportLabelExtractor()
    surface: dict[tuple[str, int], SurfaceClause] = {}
    mention_keys: set[tuple[str, int, str]] = set()
    proposition_keys: set[tuple[str, int, str]] = set()
    failure_rows: list[dict[str, object]] = []
    clause_rows: list[dict[str, object]] = []
    for record in reports[["StudyInstanceUID", "Report"]].to_dict("records"):
        uid = str(record["StudyInstanceUID"])
        report = record["Report"] if isinstance(record["Report"], str) else ""
        clauses = align_surface_clauses(report)
        for clause in clauses:
            surface[(uid, clause.source_index)] = clause
            clause_rows.append({
                "StudyInstanceUID": uid,
                "source_index": clause.source_index,
                "raw_clause": clause.raw_clause,
                "normalized_clause": clause.normalized_clause,
                "diagnostic": clause.diagnostic,
                "section": clause.section,
                "alignment_verified": clause.aligned,
            })
            if not clause.aligned:
                failure_rows.append({
                    "StudyInstanceUID": uid,
                    "source_index": clause.source_index,
                    "raw_clause": clause.raw_clause,
                    "expected_normalized_clause": clause.normalized_clause,
                    "observed_normalized_clause": normalize_text(clause.raw_clause),
                    "reason": clause.failure_reason,
                })
        mentions = list(extractor.mentions(report))
        propositions = build_propositions(mentions)
        for mention in mentions:
            for index in mention.source_indices:
                mention_keys.add((uid, int(index), mention.target))
        for proposition in propositions:
            for index in proposition.source_indices:
                proposition_keys.add((uid, int(index), proposition.target))
    return (
        surface,
        mention_keys,
        proposition_keys,
        pd.DataFrame(failure_rows, columns=[
            "StudyInstanceUID", "source_index", "raw_clause",
            "expected_normalized_clause", "observed_normalized_clause", "reason",
        ]),
        pd.DataFrame(clause_rows),
    )


def _trusted_evidence_rows(evidence: pd.DataFrame) -> pd.DataFrame:
    allowed = evidence["detectors"].map(
        lambda value: bool(_json_list(value))
        and set(map(str, _json_list(value))).issubset(TRUSTED_DETECTORS)
    )
    mask = (
        evidence["is_winning_status"].astype(str).str.lower().eq("true")
        & evidence["proposition_status"].isin(TRUSTED_TEACHER_STATUSES)
        & evidence["final_status"].eq(evidence["proposition_status"])
        & evidence["view_support"].eq("strict_only")
        & ~evidence["collective"].astype(str).str.lower().eq("true")
        & ~evidence["has_conflict"].astype(str).str.lower().eq("true")
        & evidence["resolution_mode"].eq("target_specific")
        & allowed
    )
    return evidence.loc[mask].copy()


def _provenance_json(row: object) -> str:
    return _json({
        "selected_order": int(row.selected_order),
        "evidence": str(row.evidence),
        "normalized_evidence": str(row.normalized_evidence),
        "phenotype": str(row.phenotype),
        "detectors": _json_list(row.detectors),
        "rules": _json_list(row.rules),
        "source_indices": _json_list(row.source_indices),
        "spans": _json_list(row.spans),
        "rationale": str(row.rationale),
    })


def build_trusted_candidates(
    evidence: pd.DataFrame,
    surface: Mapping[tuple[str, int], SurfaceClause],
    template_map: pd.DataFrame,
    target_descriptions: Mapping[str, str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Explode selected winning propositions into aligned strict-clause rows."""
    family_lookup = template_map.set_index("StudyInstanceUID")
    rows: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    for item in _trusted_evidence_rows(evidence).itertuples(index=False):
        uid = str(item.StudyInstanceUID)
        for source_index_value in _json_list(item.source_indices):
            source_index = int(source_index_value)
            clause = surface.get((uid, source_index))
            if clause is None or not clause.aligned:
                failures.append({
                    "StudyInstanceUID": uid,
                    "source_index": source_index,
                    "target": item.target,
                    "evidence": item.evidence,
                    "reason": "missing_or_unaligned_surface_clause",
                })
                continue
            if not clause.diagnostic:
                failures.append({
                    "StudyInstanceUID": uid,
                    "source_index": source_index,
                    "target": item.target,
                    "evidence": item.evidence,
                    "reason": "non_diagnostic_clause",
                })
                continue
            if normalize_text(clause.raw_clause) != clause.normalized_clause:
                raise AssertionError("aligned raw clause does not reproduce v3 normalization")
            if str(item.normalized_evidence) != clause.normalized_clause:
                failures.append({
                    "StudyInstanceUID": uid,
                    "source_index": source_index,
                    "target": item.target,
                    "evidence": item.evidence,
                    "reason": "selected_evidence_clause_mismatch",
                })
                continue
            detectors = [str(value) for value in _json_list(item.detectors)]
            rules = [str(value) for value in _json_list(item.rules)]
            normalized_hash = _sha256_text(clause.normalized_clause)
            example_id = _sha256_text(
                f"teacher|{uid}|{source_index}|{item.target}|{item.proposition_status}|{normalized_hash}"
            )
            rows.append({
                "example_id": example_id,
                "StudyInstanceUID": uid,
                "source_index": source_index,
                "raw_clause": clause.raw_clause,
                "normalized_clause": clause.normalized_clause,
                "normalized_clause_sha256": normalized_hash,
                "target": item.target,
                "target_description": target_descriptions[str(item.target)],
                "label": item.proposition_status,
                "original_v3_status": item.proposition_status,
                "phenotype": item.phenotype,
                "detectors": _json(detectors),
                "detector_combination": "|".join(detectors),
                "rules": _json(rules),
                "language_group": item.report_language_group,
                "view_kind": "strict",
                "collective": False,
                "conflict": False,
                "teacher_confidence": float(item.proposition_confidence),
                "evidence_provenance": _provenance_json(item),
                "report_sha256": item.report_sha256,
                "exact_template_family": family_lookup.at[uid, "exact_template_family"],
                "numeric_normalized_template_family": family_lookup.at[uid, "numeric_normalized_template_family"],
                "teacher_source_type": "v3_selected_winning_proposition",
                "no_evidence_source": "",
                "source_evidence_targets": "[]",
                "labeled_clause_targets": "[]",
                "no_evidence_guards": "[]",
                "alignment_verified": True,
            })
    return (
        pd.DataFrame(rows, columns=CANDIDATE_COLUMNS),
        pd.DataFrame(failures, columns=[
            "StudyInstanceUID", "source_index", "target", "evidence", "reason",
        ]),
    )


def collapse_trusted_clause_examples(trusted: pd.DataFrame) -> pd.DataFrame:
    """Merge multiple winning provenance entries for one local training unit."""
    if trusted.empty:
        return trusted.copy()
    rows: list[dict[str, object]] = []
    keys = [
        "StudyInstanceUID", "source_index", "target", "label", "normalized_clause",
    ]
    for _, part in trusted.groupby(keys, sort=True):
        ordered = part.sort_values(["example_id", "detector_combination", "phenotype"])
        row = ordered.iloc[0].to_dict()
        detectors = sorted({
            str(value)
            for serialized in ordered["detectors"]
            for value in _json_list(serialized)
        }, key=lambda value: -DETECTOR_PRIORITY.get(value, 0))
        rules = sorted({
            str(value)
            for serialized in ordered["rules"]
            for value in _json_list(serialized)
        })
        phenotypes = sorted({str(value) for value in ordered["phenotype"] if str(value)})
        provenances = [json.loads(str(value)) for value in ordered["evidence_provenance"]]
        row["detectors"] = _json(detectors)
        row["detector_combination"] = "|".join(detectors)
        row["rules"] = _json(rules)
        row["phenotype"] = "|".join(phenotypes)
        row["teacher_confidence"] = float(pd.to_numeric(ordered["teacher_confidence"]).max())
        row["evidence_provenance"] = _json(provenances)
        row["example_id"] = _sha256_text(
            f"teacher|{row['StudyInstanceUID']}|{row['source_index']}|{row['target']}|"
            f"{row['label']}|{row['normalized_clause_sha256']}"
        )
        rows.append(row)
    return pd.DataFrame(rows, columns=CANDIDATE_COLUMNS)


def target_has_explicit_cue(target: str, normalized_clause: str) -> bool:
    """Conservative no-evidence guard based only on the existing v3 ontology."""
    if target in ANATOMY_TERMS and contains_any(normalized_clause, ANATOMY_TERMS[target]):
        return True
    if target in DIRECT_TERMS and contains_any(normalized_clause, DIRECT_TERMS[target]):
        return True
    structural_root = STRUCTURAL_ANATOMY_ROOTS.get(target)
    if structural_root and re.search(structural_root, normalized_clause):
        return True
    oa_root = OA_ANATOMY_PATTERNS.get(target)
    if oa_root and re.search(oa_root, normalized_clause):
        return True
    if any(rule.target == target and rule.compiled().search(normalized_clause) for rule in DIRECT_RULES):
        return True
    return False


def generate_contrastive_no_evidence(
    trusted: pd.DataFrame,
    mention_keys: set[tuple[str, int, str]],
    proposition_keys: set[tuple[str, int, str]],
    target_descriptions: Mapping[str, str],
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate one deterministic, approximately target-balanced contrast per clause."""
    if trusted.empty:
        return pd.DataFrame(columns=CANDIDATE_COLUMNS), pd.DataFrame()
    counts: Counter[str] = Counter()
    output: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    group_columns = ["StudyInstanceUID", "source_index", "normalized_clause"]
    groups = list(trusted.groupby(group_columns, sort=False))
    groups.sort(key=lambda pair: _stable_hash(seed, *pair[0]))
    for (uid, source_index, normalized_clause), part in groups:
        labeled_targets = sorted(set(part["target"].astype(str)))
        candidates: list[str] = []
        rejected = Counter()
        for target in TARGETS:
            if target in labeled_targets:
                rejected["already_labeled"] += 1
            elif (str(uid), int(source_index), target) in mention_keys:
                rejected["has_v3_mention"] += 1
            elif (str(uid), int(source_index), target) in proposition_keys:
                rejected["has_v3_proposition"] += 1
            elif target_has_explicit_cue(target, str(normalized_clause)):
                rejected["explicit_target_cue"] += 1
            else:
                candidates.append(target)
        if not candidates:
            summary_rows.append({
                "StudyInstanceUID": uid,
                "source_index": source_index,
                "generated": False,
                "selected_target": "",
                "safe_candidate_count": 0,
                "labeled_clause_targets": _json(labeled_targets),
                "rejection_counts": _json(dict(rejected)),
            })
            continue
        minimum = min(counts[target] for target in candidates)
        balanced = [target for target in candidates if counts[target] == minimum]
        target = min(balanced, key=lambda value: _stable_hash(seed, uid, source_index, value))
        counts[target] += 1
        representative = part.sort_values(["target", "example_id"]).iloc[0].to_dict()
        representative.update({
            "example_id": _sha256_text(
                f"contrastive|{uid}|{source_index}|{target}|{representative['normalized_clause_sha256']}"
            ),
            "target": target,
            "target_description": target_descriptions[target],
            "label": "no_evidence",
            "original_v3_status": "not_applicable_contrastive",
            "phenotype": "",
            "detectors": "[]",
            "detector_combination": "contrastive_other_target",
            "rules": "[]",
            "teacher_confidence": "",
            "evidence_provenance": _json({
                "construction": "contrastive_other_target",
                "source_example_ids": sorted(part["example_id"].astype(str).tolist()),
            }),
            "teacher_source_type": "constructed_contrastive_no_evidence",
            "no_evidence_source": "contrastive_other_target",
            "source_evidence_targets": _json(labeled_targets),
            "labeled_clause_targets": _json(labeled_targets),
            "no_evidence_guards": _json([
                "different_from_all_labeled_targets",
                "no_selected_evidence_for_candidate",
                "no_v3_mention_for_candidate",
                "no_v3_proposition_for_candidate",
                "no_explicit_v3_target_cue",
                "not_derived_from_study_target_unknown",
            ]),
        })
        output.append(representative)
        summary_rows.append({
            "StudyInstanceUID": uid,
            "source_index": source_index,
            "generated": True,
            "selected_target": target,
            "safe_candidate_count": len(candidates),
            "labeled_clause_targets": _json(labeled_targets),
            "rejection_counts": _json(dict(rejected)),
        })
    return (
        pd.DataFrame(output, columns=CANDIDATE_COLUMNS),
        pd.DataFrame(summary_rows),
    )


def deduplicate_training_examples(
    train_source: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Surface label collisions and collapse repeated train text deterministically."""
    collision_key = ["target", "normalized_clause"]
    label_counts = train_source.groupby(collision_key)["label"].nunique()
    collision_keys = set(label_counts[label_counts > 1].index)
    collision_mask = train_source.apply(
        lambda row: (row["target"], row["normalized_clause"]) in collision_keys,
        axis=1,
    )
    collisions = train_source.loc[collision_mask].sort_values(
        ["target", "normalized_clause", "label", "StudyInstanceUID", "source_index", "example_id"]
    ).reset_index(drop=True)
    clean = train_source.loc[~collision_mask].copy()
    dedup_rows: list[dict[str, object]] = []
    for _, part in clean.groupby(["target", "label", "normalized_clause"], sort=True):
        ordered = part.sort_values(["StudyInstanceUID", "source_index", "example_id"])
        row = ordered.iloc[0].to_dict()
        studies = sorted(ordered["StudyInstanceUID"].astype(str).unique().tolist())
        row["duplicate_count"] = len(ordered)
        row["unique_study_count"] = len(studies)
        row["source_studies"] = _json(studies) if len(studies) <= 100 else ""
        row["source_studies_sha256"] = _sha256_text("\n".join(studies))
        dedup_rows.append(row)
    dedup = pd.DataFrame(dedup_rows)
    summary = pd.DataFrame([
        {"measure": "train_source_rows", "value": len(train_source)},
        {"measure": "collision_keys", "value": len(collision_keys)},
        {"measure": "collision_rows_excluded", "value": int(collision_mask.sum())},
        {"measure": "train_rows_after_collision_exclusion", "value": len(clean)},
        {"measure": "train_rows_after_dedup", "value": len(dedup)},
        {"measure": "duplicate_excess_removed", "value": len(clean) - len(dedup)},
    ])
    return dedup, collisions, summary


def annotate_test_novelty(test: pd.DataFrame, train_source: pd.DataFrame) -> pd.DataFrame:
    train_keys = set(zip(train_source["target"], train_source["normalized_clause"]))
    output = test.copy()
    output["seen_in_train"] = [
        (target, clause) in train_keys
        for target, clause in zip(output["target"], output["normalized_clause"])
    ]
    output["novel_exact_target_clause"] = ~output["seen_in_train"]
    train_counts = train_source.groupby(["target", "normalized_clause"]).size().to_dict()
    output["train_source_duplicate_count"] = [
        int(train_counts.get((target, clause), 0))
        for target, clause in zip(output["target"], output["normalized_clause"])
    ]
    test_counts = output.groupby(["target", "label", "normalized_clause"])["example_id"].transform("size")
    output["test_duplicate_count"] = test_counts.astype(int)
    return output


def unique_evaluation_slice(examples: pd.DataFrame) -> pd.DataFrame:
    return examples.sort_values(
        ["target", "label", "normalized_clause", "StudyInstanceUID", "source_index", "example_id"]
    ).drop_duplicates(["target", "label", "normalized_clause"], keep="first")


def build_stage04_datasets(
    train_path: Path,
    supervision_path: Path,
    evidence_inventory_path: Path,
    target_descriptions: Mapping[str, str],
    seed: int,
) -> dict[str, object]:
    """Build all pre-model tables without loading official/final label values."""
    if set(target_descriptions) != set(TARGETS):
        raise ValueError("target description mapping differs from the 12 policy targets")
    excluded = identify_official_studies(supervision_path)
    reports = pd.read_csv(
        train_path,
        usecols=["StudyInstanceUID", "Report"],
        dtype={"StudyInstanceUID": str, "Report": str},
        keep_default_na=False,
    )
    reports = reports.loc[~reports["StudyInstanceUID"].isin(excluded)].reset_index(drop=True)
    reports["language_group"] = reports["Report"].map(language_group)
    templates = build_template_map(reports)
    surface, mentions, propositions, alignment_failures, clauses = _runtime_guards(reports)
    evidence = pd.read_csv(evidence_inventory_path, dtype={"StudyInstanceUID": str})
    evidence = evidence.loc[~evidence["StudyInstanceUID"].isin(excluded)].copy()
    if set(evidence["final_status"].dropna()) - {"positive", "negative", "uncertain", "unknown"}:
        raise ValueError("unexpected upstream status")
    trusted, evidence_failures = build_trusted_candidates(
        evidence, surface, templates, target_descriptions,
    )
    trusted = collapse_trusted_clause_examples(trusted)
    contrastive, contrastive_summary = generate_contrastive_no_evidence(
        trusted, mentions, propositions, target_descriptions, seed,
    )
    candidates = pd.concat([trusted, contrastive], ignore_index=True)
    if candidates["example_id"].duplicated().any():
        raise ValueError("candidate example IDs are not unique")
    combined_failures = pd.concat([
        alignment_failures.assign(target="", evidence=""),
        evidence_failures.assign(
            raw_clause="", expected_normalized_clause="", observed_normalized_clause="",
        ),
    ], ignore_index=True, sort=False)
    return {
        "reports": reports,
        "templates": templates,
        "strict_clauses": clauses,
        "candidate_examples": candidates,
        "alignment_failures": combined_failures,
        "no_evidence_generation_summary": contrastive_summary,
        "excluded_official_studies": sorted(excluded),
        "upstream_policy_version": UPSTREAM_POLICY_VERSION,
    }
