"""Stable identifiers shared by the Stage 04 implementation."""

from __future__ import annotations

STAGE_VERSION = "report-label-model-baseline-v1.0.0"
UPSTREAM_POLICY_VERSION = "report-label-policy-v3.0.0"
VALID_LOCAL_LABELS = ("negative", "positive", "uncertain", "no_evidence")
TRUSTED_TEACHER_STATUSES = frozenset(("positive", "negative", "uncertain"))
TRUSTED_DETECTORS = frozenset(("v2_exact", "v3_target", "v3_morphology"))
SPLITS = ("train", "validation", "test")

