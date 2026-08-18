from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

from src.report_label_model.aggregation import aggregate_clause_predictions, aggregate_labels
from src.report_label_model.dataset import (
    CANDIDATE_COLUMNS,
    _trusted_evidence_rows,
    align_surface_clauses,
    annotate_test_novelty,
    build_template_map,
    build_trusted_candidates,
    collapse_trusted_clause_examples,
    deduplicate_training_examples,
    generate_contrastive_no_evidence,
    identify_official_studies,
    target_has_explicit_cue,
)
from src.report_label_model.evaluation import metric_bundle, mean_per_target_macro_f1
from src.report_label_model.metadata import sha256_file
from src.report_label_model.modeling import PairDataset, model_pair
from src.report_label_model.splitting import (
    apply_split_manifest,
    assign_grouped_splits,
    audit_split_assignments,
)
from src.report_label_model.training import sampling_weights
from src.report_labels.constants import TARGETS


def candidate(
    uid: str,
    source_index: int,
    target: str,
    label: str,
    clause: str,
) -> dict[str, object]:
    row = {column: "" for column in CANDIDATE_COLUMNS}
    row.update({
        "example_id": f"{uid}-{source_index}-{target}-{label}",
        "StudyInstanceUID": uid,
        "source_index": source_index,
        "raw_clause": clause,
        "normalized_clause": clause.lower(),
        "normalized_clause_sha256": f"hash-{clause.lower()}",
        "target": target,
        "target_description": f"description {target}",
        "label": label,
        "language_group": "english",
        "alignment_verified": True,
    })
    return row


class DatasetConstructionTests(unittest.TestCase):
    def test_surface_alignment_preserves_unicode_case_and_punctuation(self) -> None:
        clauses = align_surface_clauses("Hallazgos: Rotura del LCA. Derramé articular leve.")
        self.assertEqual(clauses[0].raw_clause, "Hallazgos: Rotura del LCA.")
        self.assertEqual(clauses[1].raw_clause, "Derramé articular leve.")
        self.assertTrue(all(item.aligned for item in clauses))
        self.assertTrue(all(item.diagnostic for item in clauses))

    def test_structural_rewrite_is_audited_not_fuzzy_aligned(self) -> None:
        clauses = align_surface_clauses("Findings: ACL; intact.")
        self.assertTrue(any(not item.aligned for item in clauses))

    def test_teacher_filter_is_strict_diagnostic_noncollective_and_conflict_free(self) -> None:
        base = {
            "is_winning_status": True,
            "proposition_status": "positive",
            "final_status": "positive",
            "view_support": "strict_only",
            "collective": False,
            "has_conflict": False,
            "resolution_mode": "target_specific",
            "detectors": json.dumps(["v2_exact", "v3_target"]),
        }
        rows = [base]
        rows.append({**base, "view_support": "linked_only"})
        rows.append({**base, "collective": True})
        rows.append({**base, "has_conflict": True})
        rows.append({**base, "proposition_status": "unknown", "final_status": "unknown"})
        rows.append({**base, "detectors": json.dumps(["v2_collective"])})
        selected = _trusted_evidence_rows(pd.DataFrame(rows))
        self.assertEqual(len(selected), 1)

    def test_multiple_winning_provenances_collapse_to_one_local_unit(self) -> None:
        first = candidate("s", 0, "ACL", "positive", "acl tear.")
        first.update({
            "detectors": json.dumps(["v2_exact"]),
            "rules": json.dumps(["rule_a"]),
            "phenotype": "tear",
            "teacher_confidence": 0.8,
            "evidence_provenance": json.dumps({"source": "a"}),
        })
        second = {**first,
            "example_id": "second",
            "detectors": json.dumps(["v3_target"]),
            "rules": json.dumps(["rule_b"]),
            "teacher_confidence": 0.9,
            "evidence_provenance": json.dumps({"source": "b"}),
        }
        collapsed = collapse_trusted_clause_examples(pd.DataFrame([first, second]))
        self.assertEqual(len(collapsed), 1)
        self.assertEqual(json.loads(collapsed.iloc[0]["detectors"]), ["v3_target", "v2_exact"])
        self.assertEqual(float(collapsed.iloc[0]["teacher_confidence"]), 0.9)
        self.assertEqual(len(json.loads(collapsed.iloc[0]["evidence_provenance"])), 2)

    def test_non_diagnostic_clause_is_excluded(self) -> None:
        uid = "history-only"
        report = "Clinical history: ACL tear."
        clause = align_surface_clauses(report)[0]
        self.assertFalse(clause.diagnostic)
        evidence = pd.DataFrame([{
            "StudyInstanceUID": uid,
            "target": "ACL",
            "final_status": "positive",
            "selected_order": 0,
            "proposition_status": "positive",
            "is_winning_status": True,
            "evidence": clause.normalized_clause,
            "normalized_evidence": clause.normalized_clause,
            "phenotype": "tear",
            "detectors": json.dumps(["v2_exact"]),
            "view_support": "strict_only",
            "source_indices": json.dumps([0]),
            "spans": "[]",
            "proposition_confidence": 0.9,
            "collective": False,
            "rules": "[]",
            "report_language_group": "english",
            "rationale": "v3 target-specific positive proposition",
            "has_conflict": False,
            "resolution_mode": "target_specific",
            "report_sha256": "report-hash",
        }])
        reports = pd.DataFrame([{"StudyInstanceUID": uid, "Report": report}])
        trusted, failures = build_trusted_candidates(
            evidence,
            {(uid, 0): clause},
            build_template_map(reports),
            {target: f"description {target}" for target in TARGETS},
        )
        self.assertTrue(trusted.empty)
        self.assertEqual(failures.iloc[0]["reason"], "non_diagnostic_clause")

    def test_official_values_are_not_needed_to_build_exclusion_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "supervision.csv"
            pd.DataFrame({
                "StudyInstanceUID": ["gold", "weak"],
                "final_source": ["official", "report_derived"],
                "official_label": [1, np.nan],
                "final_label": [1, 0],
            }).to_csv(path, index=False)
            self.assertEqual(identify_official_studies(path), {"gold"})


class NoEvidenceTests(unittest.TestCase):
    def test_no_evidence_requires_other_target_and_all_guards(self) -> None:
        trusted = pd.DataFrame([candidate("s1", 0, "ACL", "positive", "acl tear.")])
        mention_keys = {("s1", 0, target) for target in TARGETS if target not in {"ACL", "MCL"}}
        proposition_keys = set(mention_keys)
        descriptions = {target: f"description {target}" for target in TARGETS}
        generated, _ = generate_contrastive_no_evidence(
            trusted, mention_keys, proposition_keys, descriptions, seed=17,
        )
        self.assertEqual(len(generated), 1)
        self.assertEqual(generated.iloc[0]["target"], "MCL")
        self.assertEqual(generated.iloc[0]["label"], "no_evidence")
        self.assertEqual(generated.iloc[0]["no_evidence_source"], "contrastive_other_target")
        guards = json.loads(generated.iloc[0]["no_evidence_guards"])
        self.assertIn("not_derived_from_study_target_unknown", guards)

    def test_explicit_target_cues_fail_guard(self) -> None:
        self.assertTrue(target_has_explicit_cue("ACL", "the acl is not visualized."))
        self.assertTrue(target_has_explicit_cue("Effusion", "small joint effusion."))
        self.assertFalse(target_has_explicit_cue("Fracture", "moderate joint effusion."))
        self.assertTrue(target_has_explicit_cue("Synovitis", "minimal sinovyal kalinlasma."))

    def test_generation_is_deterministic(self) -> None:
        trusted = pd.DataFrame([candidate("s1", 0, "Effusion", "positive", "joint effusion.")])
        descriptions = {target: f"description {target}" for target in TARGETS}
        first, _ = generate_contrastive_no_evidence(trusted, set(), set(), descriptions, 19)
        second, _ = generate_contrastive_no_evidence(trusted, set(), set(), descriptions, 19)
        pd.testing.assert_frame_equal(first, second)


class SplitAndDedupTests(unittest.TestCase):
    def setUp(self) -> None:
        records = []
        rows = []
        for index in range(15):
            uid = f"s{index:02d}"
            report = "Duplicate report." if index in {0, 1} else f"Unique report {chr(65 + index)}."
            records.append({"StudyInstanceUID": uid, "Report": report, "language_group": "english"})
            rows.append(candidate(uid, 0, "ACL", "positive" if index % 2 else "negative", f"clause {index}."))
        self.reports = pd.DataFrame(records)
        self.templates = build_template_map(self.reports)
        self.candidates = pd.DataFrame(rows)

    def test_grouped_split_is_deterministic_and_duplicate_safe(self) -> None:
        ratios = {"train": 0.7, "validation": 0.15, "test": 0.15}
        first = assign_grouped_splits(self.reports, self.templates, self.candidates, ratios, 23)
        second = assign_grouped_splits(self.reports, self.templates, self.candidates, ratios, 23)
        pd.testing.assert_frame_equal(first, second)
        duplicate_splits = first[first["StudyInstanceUID"].isin(["s00", "s01"])]["split"]
        self.assertEqual(duplicate_splits.nunique(), 1)
        audit = audit_split_assignments(first, self.candidates, second, minimum_groups_for_full_support=100)
        self.assertTrue(audit["passed"].all())
        merged = apply_split_manifest(self.candidates, first)
        self.assertEqual(len(merged), len(self.candidates))

    def test_dedup_counts_and_collisions(self) -> None:
        rows = [
            candidate("a", 0, "ACL", "positive", "same."),
            candidate("b", 0, "ACL", "positive", "same."),
            candidate("c", 0, "MCL", "positive", "collision."),
            candidate("d", 0, "MCL", "negative", "collision."),
        ]
        dedup, collisions, summary = deduplicate_training_examples(pd.DataFrame(rows))
        self.assertEqual(len(dedup), 1)
        self.assertEqual(int(dedup.iloc[0]["duplicate_count"]), 2)
        self.assertEqual(int(dedup.iloc[0]["unique_study_count"]), 2)
        self.assertEqual(len(collisions), 2)
        self.assertEqual(summary.set_index("measure").at["collision_keys", "value"], 1)

    def test_test_novel_is_compared_with_train_source_before_dedup(self) -> None:
        train = pd.DataFrame([candidate("a", 0, "ACL", "positive", "seen.")])
        test = pd.DataFrame([
            candidate("b", 0, "ACL", "positive", "seen."),
            candidate("c", 0, "MCL", "positive", "seen."),
        ])
        annotated = annotate_test_novelty(test, train)
        self.assertFalse(bool(annotated.iloc[0]["novel_exact_target_clause"]))
        self.assertTrue(bool(annotated.iloc[1]["novel_exact_target_clause"]))


class ModelAggregationMetricTests(unittest.TestCase):
    def test_model_pair_contains_no_teacher_metadata(self) -> None:
        row = {
            "target_description": "anterior cruciate ligament abnormality",
            "raw_clause": "ACL is intact.",
            "detector": "must-not-enter",
            "language_group": "must-not-enter",
        }
        self.assertEqual(model_pair(row), (
            "anterior cruciate ligament abnormality", "ACL is intact.",
        ))

        class Tokenizer:
            def __init__(self) -> None:
                self.call = None

            def __call__(self, text, text_pair, **kwargs):
                self.call = (text, text_pair, kwargs)
                return {"input_ids": [1, 2], "attention_mask": [1, 1]}

        tokenizer = Tokenizer()
        dataset = PairDataset(pd.DataFrame([{**row, "label": "negative"}]), tokenizer, {"negative": 0}, 128)
        encoded = dataset[0]
        self.assertEqual(tokenizer.call[0:2], (row["target_description"], row["raw_clause"]))
        self.assertEqual(tokenizer.call[2]["max_length"], 128)
        self.assertEqual(encoded["labels"], 0)

    def test_aggregation_precedence(self) -> None:
        self.assertEqual(aggregate_labels(["negative", "uncertain", "positive"]), "positive")
        self.assertEqual(aggregate_labels(["negative", "uncertain"]), "uncertain")
        self.assertEqual(aggregate_labels(["negative", "no_evidence"]), "negative")
        self.assertEqual(aggregate_labels(["no_evidence", "no_evidence"]), "unknown")
        frame = pd.DataFrame({
            "StudyInstanceUID": ["s", "s"],
            "target": ["ACL", "ACL"],
            "source_index": [0, 1],
            "predicted_label": ["negative", "positive"],
        })
        self.assertEqual(aggregate_clause_predictions(frame).iloc[0]["predicted_status"], "positive")

    def test_metric_calculation_known_values(self) -> None:
        overall, by_label = metric_bundle(
            ["positive", "positive", "negative", "negative"],
            ["positive", "negative", "negative", "negative"],
            ["positive", "negative"],
        )
        self.assertAlmostEqual(overall["accuracy"], 0.75)
        positive = by_label.set_index("label").loc["positive"]
        self.assertAlmostEqual(positive["recall"], 0.5)
        score = mean_per_target_macro_f1(
            ["positive", "negative", "positive", "negative"],
            ["positive", "negative", "negative", "negative"],
            ["ACL", "ACL", "MCL", "MCL"],
            ["positive", "negative"],
        )
        self.assertGreater(score, 0.0)

    def test_sampling_weights_inverse_sqrt_with_cap(self) -> None:
        frame = pd.DataFrame({
            "target": ["ACL"] * 10 + ["MCL"],
            "label": ["positive"] * 10 + ["negative"],
        })
        weights = sampling_weights(frame, max_relative_weight=2.0)
        self.assertLessEqual(weights.max() / weights.min(), 2.0 + 1e-12)

    def test_hash_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "value.txt"
            path.write_text("stage04", encoding="utf-8")
            self.assertEqual(sha256_file(path), sha256_file(path))


if __name__ == "__main__":
    unittest.main()
