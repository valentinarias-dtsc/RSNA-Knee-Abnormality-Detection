"""Deterministic text normalization, segmentation and language grouping."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import re
import unicodedata

from .constants import DIAGNOSTIC_HEADERS, LANGUAGE_MARKERS, NON_DIAGNOSTIC_HEADERS

_SPECIAL_FOLD = str.maketrans({"ı": "i", "İ": "i", "ß": "ss", "đ": "d", "Đ": "d", "ø": "o", "æ": "ae"})
_BOUNDARY = re.compile(r"(?<=[.!?;])\s*|\n+")


def normalize_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    text = value.translate(_SPECIAL_FOLD).lower().replace("\u00ad", "")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[_/\\]+", " ", text)
    return re.sub(r"[ \t]+", " ", text).strip()


@lru_cache(maxsize=None)
def _term_pattern(term: str) -> re.Pattern[str]:
    escaped = re.escape(term).replace(r"\ ", r"\s+")
    return re.compile(rf"(?<!\w){escaped}(?!\w)")


@lru_cache(maxsize=None)
def _terms_pattern(terms: tuple[str, ...]) -> re.Pattern[str]:
    alternatives = [re.escape(term).replace(r"\ ", r"\s+") for term in terms]
    return re.compile(r"(?<!\w)(?:" + "|".join(alternatives) + r")(?!\w)")


def contains_term(text: str, term: str) -> bool:
    """Match a normalized term on loose alphanumeric boundaries."""
    return _term_pattern(term).search(text) is not None


def contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return _terms_pattern(terms).search(text) is not None


def matching_spans(text: str, terms: tuple[str, ...]) -> list[tuple[int, int]]:
    return [match.span() for match in _terms_pattern(terms).finditer(text)]


def matching_terms(text: str, terms: tuple[str, ...]) -> list[tuple[int, int, str]]:
    return [(match.start(), match.end(), match.group(0)) for match in _terms_pattern(terms).finditer(text)]


@dataclass(frozen=True)
class Clause:
    text: str
    section: str
    diagnostic: bool


def segment_report(value: object) -> list[Clause]:
    """Split a report into local clauses while retaining coarse section context."""
    normalized = normalize_text(value)
    if not normalized:
        return []

    fragments = [part.strip(" -\t") for part in _BOUNDARY.split(normalized) if part.strip()]
    clauses: list[Clause] = []
    section = "unspecified"
    diagnostic = True
    skip_next = False
    for index, fragment in enumerate(fragments):
        if skip_next:
            skip_next = False
            continue
        raw_fragment = fragment
        header_part = raw_fragment.split(":", 1)[0].strip()
        if contains_any(header_part, NON_DIAGNOSTIC_HEADERS):
            section, diagnostic = header_part[:80], False
        elif contains_any(header_part, DIAGNOSTIC_HEADERS):
            section, diagnostic = header_part[:80], True

        # Structured reports often put "Fracture:" and "None." on adjacent lines.
        if raw_fragment.endswith(":") and index + 1 < len(fragments):
            raw_fragment = f"{raw_fragment} {fragments[index + 1]}"
            skip_next = True
        clauses.append(Clause(raw_fragment, section, diagnostic))
    return clauses


def language_group(value: object) -> str:
    """Return a reproducible script/lexicon group, not a claimed language diagnosis."""
    text = normalize_text(value)
    if not text:
        return "empty"
    greek = sum("GREEK" in unicodedata.name(char, "") for char in text)
    cyrillic = sum("CYRILLIC" in unicodedata.name(char, "") for char in text)
    letters = max(1, sum(char.isalpha() for char in text))
    if greek / letters >= 0.08:
        return "greek_script"
    if cyrillic / letters >= 0.08:
        return "cyrillic_script"
    padded = f" {text} "
    scores = {name: sum(padded.count(marker) for marker in markers) for name, markers in LANGUAGE_MARKERS.items()}
    best = max(scores, key=lambda key: (scores[key], key))
    return best if scores[best] else "latin_other"
