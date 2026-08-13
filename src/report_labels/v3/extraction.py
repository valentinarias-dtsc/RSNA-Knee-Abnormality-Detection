"""Evidence-level multilingual ensemble for report-label policy v3."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re

from ..constants import (
    ANATOMY_TERMS,
    LIGAMENT_PATHOLOGY_TERMS,
    MENISCUS_PATHOLOGY_TERMS,
    NEGATION_TERMS,
    NORMALITY_TERMS,
    OA_TERMS,
    TARGETS,
)
from ..extraction import (
    _collective_mentions,
    _direct_mentions,
    _global_oa_mentions,
    _polarity_from_spans,
    _structural_mentions,
)
from ..text import Clause, contains_any, matching_spans, normalize_text, segment_report
from .constants import CONFIDENCE, POLICY_VERSION
from .morphology import (
    CARTILAGE_PATTERN,
    DIRECT_RULES,
    LIGAMENT_PATHOLOGY_PATTERN,
    LOCATIVE_MCL_EXCLUSION,
    LOCATIVE_BRIDGE,
    MENISCUS_PATHOLOGY_PATTERN,
    NORMAL_PATTERN,
    OA_ANATOMY_PATTERNS,
    OA_PATHOLOGY_PATTERN,
    STRUCTURAL_ANATOMY_ROOTS,
)
from .reconciliation import build_propositions, resolve_propositions
from .schema import Mention, Proposition, TextView
from .text import build_text_views, language_hypotheses


@dataclass(frozen=True)
class V3ExtractionResult:
    target: str
    status: str
    derived_label: int | None
    derived_score: float | None
    confidence: float
    evidence: tuple[str, ...]
    rationale: str
    phenotypes: tuple[str, ...]
    detectors: tuple[str, ...]
    evidence_provenance: tuple[dict[str, object], ...]


def report_sha256(report: object) -> str:
    return hashlib.sha256(normalize_text(report).encode("utf-8")).hexdigest()


def _confidence(status: str, detector: str, collective: bool = False) -> float:
    if status == "uncertain":
        return CONFIDENCE["uncertain"] - (0.05 if collective else 0.0)
    suffix = "positive" if status == "positive" else "negative"
    if collective:
        return CONFIDENCE[f"collective_{suffix}"]
    prefix = "exact" if detector == "v2_exact" else "morphology" if detector == "v3_morphology" else "target_rule"
    return CONFIDENCE[f"{prefix}_{suffix}"]


def _phenotype(text: str, status: str, fallback: str = "abnormality") -> str:
    if status == "negative":
        return f"{fallback}_absent"
    patterns = (
        ("avulsion", r"avulsion|avuls\w*"),
        ("fracture", r"fractur|fraktur|kirik|prijelom|prelom|\u03ba\u03b1\u03c4\u03b1\u03b3|\u0444\u0440\u0430\u043a\u0442\u0443\u0440|\u0441\u0447\u0443\u043f|\u043f\u0435\u0440\u0435\u043b\u043e\u043c"),
        ("tear", r"tear|torn|ruptur|rotur|desgarr|yirtik|puknuc|\u03c1\u03b7\u03be|\u0440\u0430\u0437\u043a\u044a\u0441|\u0441\u043a\u044a\u0441"),
        ("sprain", r"sprain|esguince|zorlan|ozljed|\u03ba\u03b1\u03ba\u03c9\u03c3"),
        ("degeneration", r"degener|dejener|mucoid|mukoid|miksoid|myxoid|meniskopat|ekfy|\u03b5\u03ba\u03c6\u03c5\u03bb|\u0434\u0435\u0433\u0435\u043d\u0435\u0440"),
        ("extrusion", r"extrus|extrud|ekstruz|\u03c5\u03c0\u03b5\u03be\u03b1\u03c1\u03b8\u03c1"),
        ("chondral_abnormality", r"chond|condr|hondr|kondr|cartil|kraakbeen|knorpel|hrskavic|kikirdak|\u03c7\u03bf\u03bd\u03b4\u03c1|\u0445\u043e\u043d\u0434\u0440|\u0445\u0440\u0443\u0449"),
    )
    for value, pattern in patterns:
        if re.search(pattern, text):
            return value
    return fallback


_V3_UNCERTAINTY = re.compile(
    r"\b(?:temsil edebilir|uyumlu olabilir|dusundurur|olabilir|pourrait representer|"
    r"moze odgovarati|mogao bi predstavljati|r o|dd)\b|\?"
)


def _v3_polarity(clause: Clause, spans: list[tuple[int, int]]) -> str:
    if _V3_UNCERTAINTY.search(clause.text):
        return "uncertain"
    return _polarity_from_spans(clause, spans)


def _decisive_phenotype(
    clause: Clause,
    spans: list[tuple[int, int]],
    status: str,
    fallback: str = "abnormality",
) -> str:
    decisive = [span for span in spans if _v3_polarity(clause, [span]) == status]
    text = " ".join(clause.text[start:end] for start, end in (decisive or spans))
    return _phenotype(text, status, fallback)


def _dedupe_spans(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    return sorted(set(spans))


def _regex_spans(text: str, pattern: str) -> list[tuple[int, int]]:
    return [match.span() for match in re.finditer(pattern, text)]


def _span_gap(first: tuple[int, int], second: tuple[int, int]) -> int:
    if first[1] <= second[0]:
        return second[0] - first[1]
    if second[1] <= first[0]:
        return first[0] - second[1]
    return 0


def _baseline_mentions(report: object, language: str) -> list[Mention]:
    """Run the frozen v2 detectors as the exact/common branch of the ensemble."""
    clauses = segment_report(report)
    sections_by_text = {clause.text: clause.section for clause in clauses}
    indices_by_text = {clause.text: index for index, clause in enumerate(clauses)}
    global_oa = _global_oa_mentions(clauses)
    output: list[Mention] = []
    for target in TARGETS:
        if target in ANATOMY_TERMS:
            detected = _structural_mentions(target, clauses)
            if target.endswith(" OA") and not detected:
                detected = global_oa
        else:
            detected = _direct_mentions(target, clauses)
        detected.extend(_collective_mentions(target, clauses))
        for item in detected:
            if (
                target in {"ACL", "MCL", "Medial Meniscus", "Lateral Meniscus"}
                and item.status in {"positive", "uncertain"}
                and not item.collective
                and not _associated(
                    target,
                    _anatomy_spans(target, item.text),
                    _pathology_spans(target, item.text),
                    item.text,
                )
            ):
                # V3's relation filter also constrains the inherited exact
                # branch; otherwise an exact word can still describe a cyst or
                # neighbouring structure merely located near the target.
                continue
            if (
                target.endswith(" OA")
                and item.status == "negative"
                and not re.search(CARTILAGE_PATTERN, item.text)
                and not contains_any(item.text, OA_TERMS)
            ):
                # "patellofemoral ligament normal" and "meniscus normal in the
                # lateral compartment" are not cartilage/OA assertions.
                continue
            detector = "v2_collective" if item.collective else "v2_exact"
            output.append(Mention(
                target=target,
                status=item.status,
                phenotype=_phenotype(item.text, item.status),
                text=item.text,
                detector=detector,
                view_kind="strict",
                language=language,
                confidence=_confidence(item.status, "v2_exact", item.collective),
                section=sections_by_text.get(item.text, "unspecified"),
                source_indices=(indices_by_text[item.text],) if item.text in indices_by_text else (),
                collective=item.collective,
                rule=item.rule,
            ))
    return output


def _direct_morphology_mentions(views: list[TextView], hypotheses: tuple[str, ...]) -> list[Mention]:
    output: list[Mention] = []
    for view in views:
        if not view.diagnostic:
            continue
        clause = Clause(view.text, view.section, True)
        for rule in DIRECT_RULES:
            # Language routes are permissive only for the common imported-English branch.
            if rule.language not in hypotheses and rule.language != "english":
                continue
            if any(re.search(exclusion, view.text) for exclusion in rule.exclusions):
                continue
            spans = [match.span() for match in rule.compiled().finditer(view.text)]
            if not spans:
                continue
            status = _v3_polarity(clause, spans)
            output.append(Mention(
                target=rule.target,
                status=status,
                phenotype=_decisive_phenotype(clause, spans, status, rule.phenotype),
                text=view.text,
                detector="v3_morphology",
                view_kind=view.kind,
                language=rule.language,
                confidence=_confidence(status, "v3_morphology"),
                section=view.section,
                source_indices=view.source_indices,
                span=spans[0],
                rule=rule.name,
            ))
    return output


def _anatomy_spans(target: str, text: str) -> list[tuple[int, int]]:
    spans = matching_spans(text, ANATOMY_TERMS[target])
    root = STRUCTURAL_ANATOMY_ROOTS.get(target)
    if root:
        spans.extend(_regex_spans(text, root))
    return _dedupe_spans(spans)


def _pathology_spans(target: str, text: str) -> list[tuple[int, int]]:
    if target.endswith("Meniscus"):
        terms, root = MENISCUS_PATHOLOGY_TERMS, MENISCUS_PATHOLOGY_PATTERN
    else:
        terms, root = LIGAMENT_PATHOLOGY_TERMS, LIGAMENT_PATHOLOGY_PATTERN
    return _dedupe_spans(matching_spans(text, terms) + _regex_spans(text, root))


def _associated(target: str, anatomy_spans: list[tuple[int, int]], finding_spans: list[tuple[int, int]], text: str) -> list[tuple[int, int]]:
    if not anatomy_spans or not finding_spans:
        return []
    competitors = ("ACL", "MCL", "Medial Meniscus", "Lateral Meniscus")
    other_spans = [span for other in competitors if other != target for span in _anatomy_spans(other, text)]
    selected: list[tuple[int, int]] = []
    for finding in finding_spans:
        own_site = min(anatomy_spans, key=lambda anatomy: _span_gap(finding, anatomy))
        own = _span_gap(finding, own_site)
        other = min((_span_gap(finding, anatomy) for anatomy in other_spans), default=10_000)
        if finding[1] <= own_site[0]:
            bridge = text[finding[1]:own_site[0]]
        elif own_site[1] <= finding[0]:
            bridge = text[own_site[1]:finding[0]]
        else:
            bridge = ""
        if finding[1] <= own_site[0] and LOCATIVE_BRIDGE.search(bridge):
            continue
        if own <= 260 and own <= other + 15:
            selected.append(finding)
    return selected


def _structural_v3_mentions(views: list[TextView], language: str) -> list[Mention]:
    output: list[Mention] = []
    targets = ("ACL", "MCL", "Medial Meniscus", "Lateral Meniscus")
    for view in views:
        if not view.diagnostic:
            continue
        clause = Clause(view.text, view.section, True)
        for target in targets:
            anatomy = _anatomy_spans(target, view.text)
            if not anatomy:
                continue
            if target == "MCL" and LOCATIVE_MCL_EXCLUSION.search(view.text):
                continue
            pathology = _associated(target, anatomy, _pathology_spans(target, view.text), view.text)
            if pathology:
                status = _v3_polarity(clause, pathology)
                output.append(Mention(
                    target=target,
                    status=status,
                    phenotype=_decisive_phenotype(clause, pathology, status),
                    text=view.text,
                    detector="v3_target",
                    view_kind=view.kind,
                    language=language,
                    confidence=_confidence(status, "v3_target"),
                    section=view.section,
                    source_indices=view.source_indices,
                    span=pathology[0],
                    rule="target_local_association",
                ))
                continue
            normal = _associated(
                target,
                anatomy,
                _dedupe_spans(matching_spans(view.text, NORMALITY_TERMS) + _regex_spans(view.text, NORMAL_PATTERN)),
                view.text,
            )
            if normal:
                output.append(Mention(
                    target=target,
                    status="negative",
                    phenotype="normal_structure",
                    text=view.text,
                    detector="v3_target",
                    view_kind=view.kind,
                    language=language,
                    confidence=_confidence("negative", "v3_target"),
                    section=view.section,
                    source_indices=view.source_indices,
                    span=normal[0],
                    rule="target_local_normality",
                ))
    return output


def _oa_mentions(views: list[TextView], language: str) -> list[Mention]:
    output: list[Mention] = []
    for view in views:
        if not view.diagnostic:
            continue
        clause = Clause(view.text, view.section, True)
        root_pathology = [
            span for span in _regex_spans(view.text, OA_PATHOLOGY_PATTERN)
            if not contains_any(view.text[span[0]:span[1]], NEGATION_TERMS)
        ]
        pathology = _dedupe_spans(matching_spans(view.text, OA_TERMS) + root_pathology)
        normality = _dedupe_spans(matching_spans(view.text, NORMALITY_TERMS) + _regex_spans(view.text, NORMAL_PATTERN))
        anatomy_by_target = {
            target: _dedupe_spans(matching_spans(view.text, ANATOMY_TERMS[target]) + _regex_spans(view.text, pattern))
            for target, pattern in OA_ANATOMY_PATTERNS.items()
        }
        for target, anatomy_pattern in OA_ANATOMY_PATTERNS.items():
            anatomy = anatomy_by_target[target]
            if not anatomy:
                continue
            other_anatomy = [
                span for other, spans in anatomy_by_target.items() if other != target for span in spans
            ]
            local_pathology = [
                span for span in pathology
                if min(_span_gap(span, site) for site in anatomy) <= 320
                and min(_span_gap(span, site) for site in anatomy)
                <= min((_span_gap(span, site) for site in other_anatomy), default=10_000) + 15
            ]
            if local_pathology:
                status = _v3_polarity(clause, local_pathology)
                output.append(Mention(
                    target=target,
                    status=status,
                    phenotype=_decisive_phenotype(clause, local_pathology, status, "chondral_abnormality"),
                    text=view.text,
                    detector="v3_target",
                    view_kind=view.kind,
                    language=language,
                    confidence=_confidence(status, "v3_target"),
                    section=view.section,
                    source_indices=view.source_indices,
                    span=local_pathology[0],
                    rule="compartment_scope",
                ))
                continue
            local_normal = [
                span for span in normality
                if min(_span_gap(span, site) for site in anatomy) <= 180
                and min(_span_gap(span, site) for site in anatomy)
                <= min((_span_gap(span, site) for site in other_anatomy), default=10_000) + 15
            ]
            if local_normal and re.search(CARTILAGE_PATTERN, view.text):
                output.append(Mention(
                    target=target,
                    status="negative",
                    phenotype="normal_cartilage",
                    text=view.text,
                    detector="v3_target",
                    view_kind=view.kind,
                    language=language,
                    confidence=_confidence("negative", "v3_target"),
                    section=view.section,
                    source_indices=view.source_indices,
                    span=local_normal[0],
                    rule="compartment_normality",
                ))
    return output


class V3ReportLabelExtractor:
    """Apply v3 without consulting official labels or MRI inputs."""

    policy_version = POLICY_VERSION

    def mentions(self, report: object) -> tuple[Mention, ...]:
        hypotheses = language_hypotheses(report)
        language = hypotheses[0] if hypotheses else "empty"
        views = build_text_views(report)
        mentions = _baseline_mentions(report, language)
        mentions.extend(_direct_morphology_mentions(views, hypotheses))
        mentions.extend(_structural_v3_mentions(views, language))
        mentions.extend(_oa_mentions(views, language))
        return tuple(mentions)

    def propositions(self, report: object) -> tuple[Proposition, ...]:
        return tuple(build_propositions(list(self.mentions(report))))

    def extract(self, report: object) -> dict[str, V3ExtractionResult]:
        propositions = list(self.propositions(report))
        output: dict[str, V3ExtractionResult] = {}
        for target in TARGETS:
            status, label, score, confidence, selected, rationale = resolve_propositions(target, propositions)
            output[target] = V3ExtractionResult(
                target=target,
                status=status,
                derived_label=label,
                derived_score=score,
                confidence=confidence,
                evidence=tuple(item.evidence for item in selected),
                rationale=rationale,
                phenotypes=tuple(dict.fromkeys(item.phenotype for item in selected)),
                detectors=tuple(dict.fromkeys(detector for item in selected for detector in item.detectors)),
                evidence_provenance=tuple(item.provenance() for item in selected),
            )
        return output

    def language_group(self, report: object) -> str:
        hypotheses = language_hypotheses(report)
        return hypotheses[0] if hypotheses else "empty"
