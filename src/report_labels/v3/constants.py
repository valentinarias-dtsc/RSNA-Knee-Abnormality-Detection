"""Declarative identifiers and confidence ranks for policy v3."""

from __future__ import annotations

from ..constants import TARGETS, VALID_FINAL_SOURCES, VALID_STATUSES

POLICY_VERSION = "report-label-policy-v3.0.0"
OUTPUT_VERSION = "v3"
POLICY_CONFIG_NAME = "policy_v3.json"

# Ordinal evidence-strength ranks, not calibrated probabilities.
CONFIDENCE = {
    "exact_positive": 0.90,
    "morphology_positive": 0.88,
    "target_rule_positive": 0.87,
    "collective_positive": 0.80,
    "exact_negative": 0.85,
    "morphology_negative": 0.83,
    "target_rule_negative": 0.82,
    "collective_negative": 0.75,
    "uncertain": 0.50,
    "conflict_penalty": 0.18,
    "unknown": 0.0,
}

DETECTOR_PRIORITY = {
    "v3_target": 4,
    "v3_morphology": 3,
    "v2_exact": 2,
    "v2_collective": 1,
}

__all__ = [
    "CONFIDENCE",
    "DETECTOR_PRIORITY",
    "OUTPUT_VERSION",
    "POLICY_CONFIG_NAME",
    "POLICY_VERSION",
    "TARGETS",
    "VALID_FINAL_SOURCES",
    "VALID_STATUSES",
]
