"""Mention deduplication and conservative target-level reconciliation."""

from __future__ import annotations

from collections import defaultdict

from .constants import CONFIDENCE, DETECTOR_PRIORITY
from .schema import Mention, Proposition


def build_propositions(mentions: list[Mention]) -> list[Proposition]:
    grouped: dict[tuple[str, str, str, str], list[Mention]] = defaultdict(list)
    for mention in mentions:
        grouped[(mention.target, mention.status, mention.phenotype, mention.text)].append(mention)
    output: list[Proposition] = []
    for (target, status, phenotype, evidence), members in grouped.items():
        output.append(Proposition(
            target=target,
            status=status,
            phenotype=phenotype,
            evidence=evidence,
            detectors=tuple(sorted({item.detector for item in members}, key=lambda value: -DETECTOR_PRIORITY.get(value, 0))),
            view_kinds=tuple(sorted({item.view_kind for item in members})),
            languages=tuple(sorted({item.language for item in members})),
            sections=tuple(sorted({item.section for item in members})),
            source_indices=tuple(sorted({index for item in members for index in item.source_indices})),
            spans=tuple(sorted({item.span for item in members if item.span is not None})),
            confidence=max(item.confidence for item in members),
            collective=all(item.collective for item in members),
            rules=tuple(sorted({item.rule for item in members if item.rule})),
        ))
    return sorted(
        output,
        key=lambda item: (
            -max(DETECTOR_PRIORITY.get(detector, 0) for detector in item.detectors),
            -item.confidence,
            item.evidence,
        ),
    )


def resolve_propositions(target: str, propositions: list[Proposition]) -> tuple[str, int | None, float | None, float, tuple[Proposition, ...], str]:
    candidates = [item for item in propositions if item.target == target]
    if not candidates:
        return "unknown", None, None, CONFIDENCE["unknown"], (), "no reliable target-specific proposition"

    statuses = {item.status for item in candidates}
    if "positive" in statuses:
        winner = "positive"
        derived_label, score = 1, 1.0
    elif "uncertain" in statuses:
        winner = "uncertain"
        derived_label, score = None, 0.50
    else:
        winner = "negative"
        derived_label, score = 0, 0.0

    winners = [item for item in candidates if item.status == winner]
    conflicts = [item for item in candidates if item.status != winner and item.evidence not in {value.evidence for value in winners}]
    selected = tuple((winners[:2] + conflicts[:1])[:3])
    confidence = max(item.confidence for item in winners)
    if conflicts:
        confidence = max(0.40, confidence - CONFIDENCE["conflict_penalty"])
    collective = all(item.collective for item in winners)
    mode = "collective" if collective else "target-specific"
    rationale = f"v3 {mode} {winner} proposition"
    if conflicts:
        rationale += " retained with conflicting proposition"
    return winner, derived_label, score, confidence, selected, rationale
