"""Version 3 report-label policy.

V3 coexists with the frozen v2 implementation.  It combines evidence at the
mention/proposition level and never interprets an absent mention as negative.
"""

from .constants import OUTPUT_VERSION, POLICY_CONFIG_NAME, POLICY_VERSION
from .extraction import V3ExtractionResult, V3ReportLabelExtractor
from .schema import Mention, Proposition, TextView

__all__ = [
    "Mention",
    "OUTPUT_VERSION",
    "POLICY_CONFIG_NAME",
    "POLICY_VERSION",
    "Proposition",
    "TextView",
    "V3ExtractionResult",
    "V3ReportLabelExtractor",
]
