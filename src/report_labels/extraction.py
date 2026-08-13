"""Interpretable target-specific report label extraction."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Iterable

from .constants import (
    ANATOMY_TERMS,
    COLLECTIVE_TERMS,
    DIRECT_TERMS,
    LIGAMENT_PATHOLOGY_TERMS,
    MENISCUS_PATHOLOGY_TERMS,
    NEGATION_TERMS,
    NORMALITY_TERMS,
    OA_TERMS,
    POLICY_VERSION,
    POSTPOSED_NEGATION_TERMS,
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


@dataclass(frozen=True)
class _Mention:
    status: str
    text: str
    collective: bool = False
    rule: str | None = None


def report_sha256(report: object) -> str:
    return hashlib.sha256(normalize_text(report).encode("utf-8")).hexdigest()


def _polarity(clause: Clause, evidence_terms: tuple[str, ...], normality_is_negative: bool = False) -> str:
    """Classify evidence using local negation around the matched finding.

    The asymmetric window handles "no tear" and "tear is not seen" without allowing
    "tear without extrusion" to negate the tear itself.
    """
    return _polarity_from_spans(clause, matching_spans(clause.text, evidence_terms), normality_is_negative)


def _polarity_from_spans(
    clause: Clause,
    evidence_spans: list[tuple[int, int]],
    normality_is_negative: bool = False,
) -> str:
    if contains_any(clause.text, UNCERTAINTY_TERMS):
        return "uncertain"
    negation_matches = matching_terms(clause.text, NEGATION_TERMS)
    if normality_is_negative and contains_any(clause.text, NORMALITY_TERMS):
        return "negative"
    span_is_negated = [
        any(
            (neg_start <= evidence_start and evidence_start - neg_end <= 90)
            or (
                neg_start >= evidence_end
                and neg_start - evidence_end <= 40
                and neg_text in POSTPOSED_NEGATION_TERMS
                and all(
                    token in {
                        "is", "are", "was", "were", "has", "been", "seen", "identified",
                        "detected", "demonstrated", "visualized", "visualised", "observed",
                        "present", "evident", "noted",
                    }
                    for token in re.findall(r"\w+", clause.text[evidence_end:neg_start])
                )
            )
            for neg_start, neg_end, neg_text in negation_matches
        )
        for evidence_start, evidence_end in evidence_spans
    ]
    # A clause may assert one abnormality while excluding another (for example,
    # "meniscal degeneration without tears"). Preserve the unnegated finding.
    if span_is_negated and all(span_is_negated):
        return "negative"
    return "positive"


def _span_gap(first: tuple[int, int], second: tuple[int, int]) -> int:
    if first[1] <= second[0]:
        return second[0] - first[1]
    if second[1] <= first[0]:
        return first[0] - second[1]
    return 0


def _target_local_spans(
    target: str,
    clause: Clause,
    candidate_terms: tuple[str, ...],
    before_limit: int,
    after_limit: int,
) -> list[tuple[int, int]]:
    target_spans = matching_spans(clause.text, ANATOMY_TERMS[target])
    all_anatomy_spans = [
        span
        for terms in ANATOMY_TERMS.values()
        for span in matching_spans(clause.text, terms)
    ]
    selected: list[tuple[int, int]] = []
    for candidate in matching_spans(clause.text, candidate_terms):
        eligible_distances = [
            _span_gap(candidate, anatomy)
            for anatomy in target_spans
            if (
                (candidate[1] <= anatomy[0] and anatomy[0] - candidate[1] <= before_limit)
                or (candidate[0] >= anatomy[1] and candidate[0] - anatomy[1] <= after_limit)
                or _span_gap(candidate, anatomy) == 0
            )
        ]
        if not eligible_distances:
            continue
        target_distance = min(eligible_distances)
        nearest_distance = min((_span_gap(candidate, anatomy) for anatomy in all_anatomy_spans), default=target_distance)
        if target_distance <= nearest_distance + 5:
            selected.append(candidate)
    return selected


def _structural_mentions(target: str, clauses: Iterable[Clause]) -> list[_Mention]:
    mentions: list[_Mention] = []
    anatomy = ANATOMY_TERMS[target]
    if target.endswith(" OA"):
        pathology = OA_TERMS
        before_limit = 100
    elif target.endswith("Meniscus"):
        pathology = MENISCUS_PATHOLOGY_TERMS
        before_limit = 120
    else:
        pathology = LIGAMENT_PATHOLOGY_TERMS
        before_limit = 30
    for clause in clauses:
        if not clause.diagnostic or not contains_any(clause.text, anatomy):
            continue
        pathology_spans = _target_local_spans(target, clause, pathology, before_limit, 160)
        if pathology_spans:
            polarity = _polarity_from_spans(clause, pathology_spans)
            mentions.append(_Mention(polarity, clause.text))
        else:
            anatomy_polarity = _polarity(clause, anatomy)
            normality_spans = _target_local_spans(target, clause, NORMALITY_TERMS, 60, 80)
            explicitly_normal = bool(normality_spans)
            # "ACL intact" and "no meniscal tear" are explicit negative assertions.
            if anatomy_polarity == "negative" or explicitly_normal:
                mentions.append(_Mention("negative", clause.text))
    return mentions


def _direct_mentions(target: str, clauses: Iterable[Clause]) -> list[_Mention]:
    mentions: list[_Mention] = []
    for clause in clauses:
        if clause.diagnostic and contains_any(clause.text, DIRECT_TERMS[target]):
            mentions.append(_Mention(_polarity(clause, DIRECT_TERMS[target]), clause.text))
    return mentions


def _global_oa_mentions(clauses: Iterable[Clause]) -> list[_Mention]:
    global_terms = (
        "tricompartmental", "tri compartmental", "all three compartments",
        "tres compartimentos", "tricompartimental", "trois compartiments",
        "tricompartimenteel", "dreikompartiment", "tum kompartman", "trikompartmantal",
        "sva tri kompartmenta", "трикомпартмент", "τρια διαμερισματα",
    )
    return [
        _Mention(_polarity(clause, OA_TERMS), clause.text)
        for clause in clauses
        if clause.diagnostic and contains_any(clause.text, global_terms) and contains_any(clause.text, OA_TERMS)
    ]


def _collective_mentions(target: str, clauses: Iterable[Clause]) -> list[_Mention]:
    """Expand explicit whole-group assertions using target-specific safety rules."""
    mentions: list[_Mention] = []
    for rule, specification in COLLECTIVE_TERMS.items():
        if target not in specification["targets"]:
            continue
        collective_terms = specification["terms"]
        pathology_terms = specification["pathology_terms"]
        for clause in clauses:
            if not clause.diagnostic or not contains_any(clause.text, collective_terms):
                continue
            # A target-specific mention in the same clause is more precise and is
            # already handled by the structural extractor. Keeping both can create
            # artificial "normal group vs abnormal member" conflicts.
            if target in ANATOMY_TERMS and contains_any(clause.text, ANATOMY_TERMS[target]):
                continue

            group_polarity = _polarity(clause, collective_terms, normality_is_negative=True)
            has_pathology = contains_any(clause.text, pathology_terms)
            if group_polarity == "negative":
                mentions.append(_Mention("negative", clause.text, True, rule))
                continue
            if not has_pathology:
                continue

            pathology_polarity = _polarity(clause, pathology_terms)
            if pathology_polarity == "negative":
                mentions.append(_Mention("negative", clause.text, True, rule))
            elif pathology_polarity == "uncertain" and specification["allow_uncertain"]:
                mentions.append(_Mention("uncertain", clause.text, True, rule))
            elif pathology_polarity == "positive" and specification["allow_positive"]:
                mentions.append(_Mention("positive", clause.text, True, rule))
    return mentions


def _resolution_evidence(mentions: list[_Mention], winning_status: str) -> tuple[str, ...]:
    winners = sorted(
        (mention for mention in mentions if mention.status == winning_status),
        key=lambda mention: mention.collective,
    )
    winner_texts = {mention.text for mention in winners}
    conflicts = [
        mention for mention in mentions
        if mention.status != winning_status and mention.text not in winner_texts
    ]
    ordered = winners[:2] + conflicts[:1] if conflicts else winners
    return tuple(dict.fromkeys(mention.text[:500] for mention in ordered))[:3]


def _resolve(target: str, mentions: list[_Mention]) -> ExtractionResult:
    statuses = [mention.status for mention in mentions]
    if "positive" in statuses:
        positive_texts = {mention.text for mention in mentions if mention.status == "positive"}
        conflict = any(mention.status != "positive" and mention.text not in positive_texts for mention in mentions)
        collective = all(mention.collective for mention in mentions if mention.status == "positive")
        evidence = _resolution_evidence(mentions, "positive")
        if conflict:
            score, confidence = (0.85, 0.65) if collective else (0.90, 0.70)
            rationale = (
                "collective positive evidence retained with conflicting mentions"
                if collective else "positive evidence retained with conflicting mentions"
            )
        else:
            score, confidence = (0.85, 0.80) if collective else (1.0, 0.90)
            rationale = "explicit collective positive evidence" if collective else "explicit positive evidence"
        return ExtractionResult(target, "positive", 1, score, confidence, evidence, rationale)
    if "uncertain" in statuses:
        uncertain_texts = {mention.text for mention in mentions if mention.status == "uncertain"}
        conflict = any(mention.status == "negative" and mention.text not in uncertain_texts for mention in mentions)
        collective = all(mention.collective for mention in mentions if mention.status == "uncertain")
        evidence = _resolution_evidence(mentions, "uncertain")
        rationale = "explicit collective uncertain evidence" if collective else "explicit uncertain evidence"
        if conflict:
            rationale += " retained with negative mentions"
        return ExtractionResult(
            target, "uncertain", None, 0.45 if collective else 0.50,
            0.45 if collective else 0.50, evidence, rationale,
        )
    if "negative" in statuses:
        collective = all(mention.collective for mention in mentions if mention.status == "negative")
        evidence = _resolution_evidence(mentions, "negative")
        return ExtractionResult(
            target, "negative", 0, 0.0, 0.75 if collective else 0.85, evidence,
            "explicit collective negation or normality" if collective else "explicit negation or normality",
        )
    return ExtractionResult(target, "unknown", None, None, 0.0, (), "no reliable target-specific evidence")


class ReportLabelExtractor:
    """Apply policy v2 without consulting official labels."""

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
            mentions.extend(_collective_mentions(target, clauses))
            output[target] = _resolve(target, mentions)
        return output

    def language_group(self, report: object) -> str:
        return language_group(report)
