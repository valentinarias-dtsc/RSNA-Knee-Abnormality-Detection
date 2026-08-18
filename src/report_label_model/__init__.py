"""Stage 04 weakly supervised target-conditioned report-label model."""

from .aggregation import aggregate_clause_predictions
from .dataset import build_stage04_datasets
from .splitting import assign_grouped_splits, audit_split_assignments

__all__ = [
    "aggregate_clause_predictions",
    "assign_grouped_splits",
    "audit_split_assignments",
    "build_stage04_datasets",
]
