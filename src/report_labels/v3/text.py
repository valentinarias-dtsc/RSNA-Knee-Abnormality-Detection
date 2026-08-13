"""Multi-view segmentation and non-exclusive language hypotheses for v3."""

from __future__ import annotations

import re
import unicodedata

from ..text import language_group, normalize_text, segment_report
from .schema import TextView

_CONTINUATION = re.compile(
    r"^(?:and|or|with|without|as well as|y|o|con|sin|et|avec|sans|und|oder|mit|ohne|"
    r"ve|veya|ile|uz|i|te|bez|kao|\u03ba\u03b1\u03b9|\u03c7\u03c9\u03c1\u03b9\u03c2|\u0438|\u0431\u0435\u0437)\b"
)


def language_hypotheses(value: object) -> tuple[str, ...]:
    """Return ranked routing hints without making language an exclusive gate."""
    text = normalize_text(value)
    primary = language_group(value)
    hypotheses = [primary]
    if any("GREEK" in unicodedata.name(char, "") for char in text):
        hypotheses.append("greek_script")
    if any("CYRILLIC" in unicodedata.name(char, "") for char in text):
        hypotheses.append("cyrillic_script")
    # Latin reports frequently contain imported English headings or terminology.
    if primary not in {"greek_script", "cyrillic_script", "english"}:
        hypotheses.append("english")
    return tuple(dict.fromkeys(hypotheses))


def build_text_views(value: object) -> list[TextView]:
    """Build strict and high-confidence linked views over the same report.

    Linked views are deliberately limited to explicit continuation cues or a
    short heading-like parent.  Arbitrary adjacent clauses are never merged.
    """
    clauses = segment_report(value)
    views = [
        TextView(clause.text, clause.section, clause.diagnostic, "strict", (index,))
        for index, clause in enumerate(clauses)
    ]
    for index, (left, right) in enumerate(zip(clauses, clauses[1:])):
        if not left.diagnostic or not right.diagnostic or left.section != right.section:
            continue
        left_words = left.text.split()
        heading_parent = left.text.rstrip().endswith(":") or (
            len(left_words) <= 7 and left.text.rstrip().endswith((",", ":"))
        )
        continuation = bool(_CONTINUATION.match(right.text))
        if not (heading_parent or continuation):
            continue
        combined = f"{left.text} {right.text}"
        if len(combined) <= 500:
            views.append(TextView(combined, left.section, True, "linked", (index, index + 1)))
    return views
