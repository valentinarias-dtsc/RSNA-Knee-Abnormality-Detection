"""Typed intermediate representation used by the v3 evidence ensemble."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextView:
    """One auditable segmentation hypothesis over diagnostic text."""

    text: str
    section: str
    diagnostic: bool
    kind: str
    source_indices: tuple[int, ...]


@dataclass(frozen=True)
class Mention:
    """A detector-local finding before target reconciliation."""

    target: str
    status: str
    phenotype: str
    text: str
    detector: str
    view_kind: str
    language: str
    confidence: float
    section: str = "unspecified"
    source_indices: tuple[int, ...] = ()
    span: tuple[int, int] | None = None
    collective: bool = False
    rule: str | None = None


@dataclass(frozen=True)
class Proposition:
    """Deduplicated clinical proposition retained for final resolution."""

    target: str
    status: str
    phenotype: str
    evidence: str
    detectors: tuple[str, ...]
    view_kinds: tuple[str, ...]
    languages: tuple[str, ...]
    sections: tuple[str, ...]
    source_indices: tuple[int, ...]
    spans: tuple[tuple[int, int], ...]
    confidence: float
    collective: bool
    rules: tuple[str, ...]

    def provenance(self) -> dict[str, object]:
        return {
            "status": self.status,
            "phenotype": self.phenotype,
            "evidence": self.evidence,
            "detectors": list(self.detectors),
            "views": list(self.view_kinds),
            "languages": list(self.languages),
            "sections": list(self.sections),
            "source_indices": list(self.source_indices),
            "spans": [list(span) for span in self.spans],
            "confidence": self.confidence,
            "collective": self.collective,
            "rules": list(self.rules),
        }
