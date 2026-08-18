"""Deterministic grouped split assignment and leakage audits."""

from __future__ import annotations

from collections import Counter
import hashlib
from typing import Mapping

import pandas as pd

from .constants import SPLITS


def _stable_hash(seed: int, *values: object) -> str:
    payload = "|".join([str(seed), *(str(value) for value in values)])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _validate_ratios(ratios: Mapping[str, float]) -> dict[str, float]:
    if set(ratios) != set(SPLITS):
        raise ValueError(f"split ratios must define {SPLITS}")
    output = {name: float(ratios[name]) for name in SPLITS}
    if any(value <= 0 for value in output.values()) or abs(sum(output.values()) - 1.0) > 1e-9:
        raise ValueError("split ratios must be positive and sum to one")
    return output


def _group_feature_counters(
    studies: pd.DataFrame,
    candidates: pd.DataFrame,
) -> tuple[dict[str, Counter[str]], Counter[str]]:
    candidate_by_study: dict[str, Counter[str]] = {}
    for uid, part in candidates.groupby("StudyInstanceUID", sort=False):
        candidate_by_study[str(uid)] = Counter(
            f"target_label:{target}|{label}"
            for target, label in zip(part["target"], part["label"])
        )
    group_features: dict[str, Counter[str]] = {}
    totals: Counter[str] = Counter()
    for group_id, members in studies.groupby("split_group_id", sort=True):
        features: Counter[str] = Counter()
        features["__studies__"] = len(members)
        if len(members) > 1:
            features["__duplicate_studies__"] = len(members)
            features["__duplicate_families__"] = 1
        for row in members.itertuples(index=False):
            features[f"language:{row.language_group}"] += 1
            features.update(candidate_by_study.get(str(row.StudyInstanceUID), Counter()))
        group_features[str(group_id)] = features
        totals.update(features)
    return group_features, totals


def assign_grouped_splits(
    reports: pd.DataFrame,
    template_map: pd.DataFrame,
    candidates: pd.DataFrame,
    ratios: Mapping[str, float],
    seed: int,
) -> pd.DataFrame:
    """Greedily approximate language and target/status ratios over indivisible groups.

    Numeric-normalized report families subsume exact duplicates and are the
    indivisible grouping unit.  Singleton reports receive a Study-specific ID.
    Groups are ordered by feature rarity, then assigned to the split that
    minimises normalized squared deviation from all requested feature totals.
    """
    ratios = _validate_ratios(ratios)
    required_reports = {"StudyInstanceUID", "language_group"}
    required_templates = {
        "StudyInstanceUID", "exact_template_family", "numeric_normalized_template_family",
    }
    if missing := required_reports - set(reports.columns):
        raise ValueError(f"reports missing split columns: {sorted(missing)}")
    if missing := required_templates - set(template_map.columns):
        raise ValueError(f"template map missing columns: {sorted(missing)}")
    studies = reports[["StudyInstanceUID", "language_group"]].copy()
    studies["StudyInstanceUID"] = studies["StudyInstanceUID"].astype(str)
    studies = studies.merge(template_map[list(required_templates)], on="StudyInstanceUID", validate="one_to_one")
    family_sizes = studies.groupby("numeric_normalized_template_family")["StudyInstanceUID"].transform("size")
    studies["template_family"] = studies["numeric_normalized_template_family"]
    studies["split_group_id"] = [
        f"template:{family}" if size > 1 else f"study:{uid}"
        for uid, family, size in zip(
            studies["StudyInstanceUID"], studies["numeric_normalized_template_family"], family_sizes,
        )
    ]
    group_features, totals = _group_feature_counters(studies, candidates)
    rarity = {
        group: sum(value / max(totals[feature], 1) for feature, value in features.items())
        for group, features in group_features.items()
    }
    order = sorted(
        group_features,
        key=lambda group: (
            -rarity[group],
            -group_features[group]["__studies__"],
            _stable_hash(seed, group),
        ),
    )
    assigned = {split: Counter() for split in SPLITS}
    group_assignment: dict[str, str] = {}

    def objective(candidate_split: str, group: str) -> float:
        score = 0.0
        for split in SPLITS:
            for feature, total in totals.items():
                value = assigned[split][feature]
                if split == candidate_split:
                    value += group_features[group][feature]
                desired = total * ratios[split]
                scale = max(desired, 1.0)
                feature_weight = 4.0 if feature == "__studies__" else 1.0
                score += feature_weight * ((value - desired) / scale) ** 2
                if value > desired:
                    score += feature_weight * 0.05 * ((value - desired) / scale) ** 2
        return score

    # Allocate duplicate families first so that large template groups cannot
    # all be absorbed by the held-out targets of other strata.  This inner
    # greedy objective balances both duplicated Studies and family counts.
    duplicate_groups = [group for group in order if group_features[group]["__duplicate_families__"]]

    def duplicate_objective(candidate_split: str, group: str) -> float:
        score = 0.0
        for split in SPLITS:
            for feature, weight in (("__duplicate_studies__", 4.0), ("__duplicate_families__", 4.0)):
                value = assigned[split][feature]
                if split == candidate_split:
                    value += group_features[group][feature]
                desired = totals[feature] * ratios[split]
                score += weight * ((value - desired) / max(float(totals[feature]), 1.0)) ** 2
        return score

    for group in sorted(
        duplicate_groups,
        key=lambda value: (-group_features[value]["__duplicate_studies__"], _stable_hash(seed, value)),
    ):
        selected = min(
            SPLITS,
            key=lambda split: (duplicate_objective(split, group), _stable_hash(seed, group, split)),
        )
        group_assignment[group] = selected
        assigned[selected].update(group_features[group])

    def duplicate_total_cost() -> float:
        score = 0.0
        for split in SPLITS:
            for feature, weight in (("__duplicate_studies__", 4.0), ("__duplicate_families__", 4.0)):
                desired = totals[feature] * ratios[split]
                scale = max(float(totals[feature]), 1.0)
                score += weight * ((assigned[split][feature] - desired) / scale) ** 2
        return score

    # Deterministic single-family local improvement corrects early greedy
    # choices made before the remaining family-size distribution is known.
    for _ in range(200):
        current_cost = duplicate_total_cost()
        moves: list[tuple[float, str, str, str]] = []
        for group in duplicate_groups:
            source = group_assignment[group]
            for destination in SPLITS:
                if destination == source:
                    continue
                assigned[source].subtract(group_features[group])
                assigned[destination].update(group_features[group])
                cost = duplicate_total_cost()
                assigned[destination].subtract(group_features[group])
                assigned[source].update(group_features[group])
                moves.append((cost, _stable_hash(seed, group, destination), group, destination))
        best_cost, _, best_group, best_destination = min(moves)
        if best_cost >= current_cost - 1e-15:
            break
        source = group_assignment[best_group]
        assigned[source].subtract(group_features[best_group])
        assigned[best_destination].update(group_features[best_group])
        group_assignment[best_group] = best_destination

    # Seed any still-empty split for tiny test/smoke corpora.
    seeded = set(group_assignment)
    for split in SPLITS:
        if assigned[split]["__studies__"]:
            continue
        group = next(value for value in order if value not in seeded)
        group_assignment[group] = split
        assigned[split].update(group_features[group])
        seeded.add(group)

    for group in order:
        if group in seeded:
            continue
        selected = min(
            SPLITS,
            key=lambda split: (objective(split, group), _stable_hash(seed, group, split)),
        )
        group_assignment[group] = selected
        assigned[selected].update(group_features[group])
    studies["split"] = studies["split_group_id"].map(group_assignment)
    return studies[[
        "StudyInstanceUID", "split_group_id", "template_family",
        "exact_template_family", "numeric_normalized_template_family",
        "language_group", "split",
    ]].sort_values("StudyInstanceUID").reset_index(drop=True)


def split_summary(assignments: pd.DataFrame, candidates: pd.DataFrame) -> pd.DataFrame:
    merged = candidates.merge(
        assignments[["StudyInstanceUID", "split"]], on="StudyInstanceUID", validate="many_to_one",
    )
    rows: list[dict[str, object]] = []
    for split in SPLITS:
        study_part = assignments[assignments["split"].eq(split)]
        example_part = merged[merged["split"].eq(split)]
        rows.append({
            "record_type": "overall",
            "split": split,
            "target": "__all__",
            "label": "__all__",
            "studies": study_part["StudyInstanceUID"].nunique(),
            "split_groups": study_part["split_group_id"].nunique(),
            "examples": len(example_part),
        })
        for (target, label), part in example_part.groupby(["target", "label"], sort=True):
            rows.append({
                "record_type": "target_label",
                "split": split,
                "target": target,
                "label": label,
                "studies": part["StudyInstanceUID"].nunique(),
                "split_groups": part.merge(
                    assignments[["StudyInstanceUID", "split_group_id"]], on="StudyInstanceUID",
                    validate="many_to_one",
                )["split_group_id"].nunique(),
                "examples": len(part),
            })
    return pd.DataFrame(rows)


def audit_split_assignments(
    assignments: pd.DataFrame,
    candidates: pd.DataFrame,
    repeated_assignments: pd.DataFrame | None = None,
    minimum_groups_for_full_support: int = 3,
) -> pd.DataFrame:
    """Return machine-readable checks and raise for any grave leakage violation."""
    checks: list[dict[str, object]] = []

    def add(name: str, violations: int, severity: str, detail: str) -> None:
        checks.append({
            "check": name,
            "passed": violations == 0,
            "violations": int(violations),
            "severity": severity,
            "detail": detail,
        })

    add(
        "study_disjointness",
        int((assignments.groupby("StudyInstanceUID")["split"].nunique() > 1).sum()),
        "error",
        "Every StudyInstanceUID must occur in exactly one split.",
    )
    duplicate_families = assignments.groupby("numeric_normalized_template_family").filter(lambda part: len(part) > 1)
    add(
        "duplicate_report_family_disjointness",
        int((duplicate_families.groupby("numeric_normalized_template_family")["split"].nunique() > 1).sum()),
        "error",
        "Exact/numeric-normalized duplicate report families are indivisible.",
    )
    add(
        "assignment_row_uniqueness",
        int(assignments["StudyInstanceUID"].duplicated().sum()),
        "error",
        "The split manifest contains one row per Study.",
    )
    merged = candidates.merge(
        assignments[["StudyInstanceUID", "split"]], on="StudyInstanceUID", how="left", validate="many_to_one",
    )
    add(
        "candidate_manifest_reconciliation",
        int(merged["split"].isna().sum()) + abs(len(merged) - len(candidates)),
        "error",
        "Every candidate reconciles to exactly one manifest row.",
    )
    add(
        "nonempty_partitions",
        sum(int(not assignments["split"].eq(split).any()) for split in SPLITS),
        "error",
        "All requested partitions contain Studies.",
    )
    if repeated_assignments is not None:
        first = assignments.sort_values("StudyInstanceUID").reset_index(drop=True)
        second = repeated_assignments.sort_values("StudyInstanceUID").reset_index(drop=True)
        reproducible = first.equals(second)
        add("deterministic_reproduction", 0 if reproducible else 1, "error", "Same inputs/config/seed reproduce the manifest.")
    candidate_groups = merged.merge(
        assignments[["StudyInstanceUID", "split_group_id"]], on="StudyInstanceUID", validate="many_to_one",
    )
    missing = 0
    evaluated = 0
    for _, part in candidate_groups.groupby(["target", "label"], sort=True):
        if part["split_group_id"].nunique() >= minimum_groups_for_full_support:
            evaluated += 1
            missing += sum(int(not part["split"].eq(split).any()) for split in SPLITS)
    add(
        "supported_target_label_presence",
        missing,
        "error",
        f"Target/label strata with >= {minimum_groups_for_full_support} groups appear in every split ({evaluated} strata checked).",
    )
    audit = pd.DataFrame(checks)
    grave = audit[audit["severity"].eq("error") & ~audit["passed"]]
    if not grave.empty:
        detail = "; ".join(f"{row.check}={row.violations}" for row in grave.itertuples())
        raise ValueError(f"split leakage/invariant audit failed: {detail}")
    return audit


def apply_split_manifest(candidates: pd.DataFrame, assignments: pd.DataFrame) -> pd.DataFrame:
    output = candidates.merge(
        assignments[["StudyInstanceUID", "split_group_id", "split"]],
        on="StudyInstanceUID",
        validate="many_to_one",
    )
    if len(output) != len(candidates):
        raise ValueError("split merge changed candidate cardinality")
    return output
