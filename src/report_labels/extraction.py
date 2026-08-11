"""Interpretable target-specific report label extraction."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Iterable

from .constants import (
    ANATOMY_TERMS,
    DIRECT_TERMS,
    NEGATION_TERMS,
    NORMALITY_TERMS,
    OA_TERMS,
    PATHOLOGY_TERMS,
    POLICY_VERSION,
    TARGETS,
    UNCERTAINTY_TERMS,
)
from .text import Clause, contains_any, language_group, matching_spans, matching_terms, normalize_text, segment_report


@dataclass(frozen=True)
class ExtractionResult:
    target: str
    status: str
    derived_label: int | None
    derived_score: float | None
    confidence: float
    evidence: tuple[str, ...]
    rationale: str


def report_sha256(report: object) -> str:
    return hashlib.sha256(normalize_text(report).encode("utf-8")).hexdigest()


def _polarity(clause: Clause, evidence_terms: tuple[str, ...], normality_is_negative: bool = False) -> str:
    """Classify evidence using local negation around the matched finding.

    The asymmetric window handles "no tear" and "tear is not seen" without allowing
    "tear without extrusion" to negate the tear itself.
    """
    if contains_any(clause.text, UNCERTAINTY_TERMS):
        return "uncertain"
    evidence_spans = matching_spans(clause.text, evidence_terms)
    negation_matches = matching_terms(clause.text, NEGATION_TERMS)
    postposed_negators = {"no", "not", "niet", "nicht", "degil", "nije", "δεν", "не"}
    negated = any(
        (neg_start <= evidence_start and evidence_start - neg_end <= 90)
        or (neg_start >= evidence_end and neg_start - evidence_end <= 40 and neg_text in postposed_negators)
        for evidence_start, evidence_end in evidence_spans
        for neg_start, neg_end, neg_text in negation_matches
    )
    if negated or (normality_is_negative and contains_any(clause.text, NORMALITY_TERMS)):
        return "negative"
    return "positive"


def _structural_mentions(target: str, clauses: Iterable[Clause]) -> list[tuple[str, str]]:
    mentions: list[tuple[str, str]] = []
    anatomy = ANATOMY_TERMS[target]
    pathology = OA_TERMS if target.endswith(" OA") else PATHOLOGY_TERMS
    for clause in clauses:
        if not clause.diagnostic or not contains_any(clause.text, anatomy):
            continue
        has_pathology = contains_any(clause.text, pathology)
        polarity = _polarity(clause, pathology)
        if has_pathology:
            mentions.append((polarity, clause.text))
        elif _polarity(clause, anatomy, normality_is_negative=True) == "negative":
            # "ACL intact" and "no meniscal tear" are explicit negative assertions.
            mentions.append(("negative", clause.text))
    return mentions


def _direct_mentions(target: str, clauses: Iterable[Clause]) -> list[tuple[str, str]]:
    mentions: list[tuple[str, str]] = []
    for clause in clauses:
        if clause.diagnostic and contains_any(clause.text, DIRECT_TERMS[target]):
            mentions.append((_polarity(clause, DIRECT_TERMS[target]), clause.text))
    return mentions


def _global_oa_mentions(clauses: Iterable[Clause]) -> list[tuple[str, str]]:
    global_terms = (
        "tricompartmental", "tri compartmental", "all three compartments",
        "tres compartimentos", "tricompartimental", "trois compartiments",
        "tricompartimenteel", "dreikompartiment", "tum kompartman",
        "sva tri kompartmenta", "трикомпартмент",
    )
    return [
        (_polarity(clause, OA_TERMS), clause.text)
        for clause in clauses
        if clause.diagnostic and contains_any(clause.text, global_terms) and contains_any(clause.text, OA_TERMS)
    ]


def _resolve(target: str, mentions: list[tuple[str, str]]) -> ExtractionResult:
    statuses = [status for status, _ in mentions]
    evidence = tuple(dict.fromkeys(text[:500] for _, text in mentions))[:3]
    if "positive" in statuses:
        conflict = "negative" in statuses or "uncertain" in statuses
        return ExtractionResult(
            target, "positive", 1, 0.90 if conflict else 1.0, 0.70 if conflict else 0.90,
            evidence, "positive evidence retained with conflicting mentions" if conflict else "explicit positive evidence",
        )
    if "uncertain" in statuses:
        return ExtractionResult(target, "uncertain", None, 0.50, 0.50, evidence, "explicit uncertain evidence")
    if "negative" in statuses:
        return ExtractionResult(target, "negative", 0, 0.0, 0.85, evidence, "explicit negation or normality")
    return ExtractionResult(target, "unknown", None, None, 0.0, (), "no reliable target-specific evidence")


class ReportLabelExtractor:
    """Apply policy v1 without consulting official labels."""

    policy_version = POLICY_VERSION

    def extract(self, report: object) -> dict[str, ExtractionResult]:
        clauses = segment_report(report)
        global_oa = _global_oa_mentions(clauses)
        output: dict[str, ExtractionResult] = {}
        for target in TARGETS:
            if target in ANATOMY_TERMS:
                mentions = _structural_mentions(target, clauses)
                if target.endswith(" OA") and not mentions:
                    mentions = global_oa
            else:
                mentions = _direct_mentions(target, clauses)
            output[target] = _resolve(target, mentions)
        return output

    def language_group(self, report: object) -> str:
        return language_group(report)
