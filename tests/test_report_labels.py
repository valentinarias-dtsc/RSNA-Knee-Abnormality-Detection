from __future__ import annotations

import unittest
import json
from pathlib import Path

import pandas as pd

from src.report_labels.constants import TARGETS
from src.report_labels.extraction import ReportLabelExtractor
from src.report_labels.pipeline import build_supervision, validate_supervision


class ExtractionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.extractor = ReportLabelExtractor()

    def test_acl_positive(self) -> None:
        result = self.extractor.extract("Findings: ACL tear.")["ACL"]
        self.assertEqual((result.status, result.derived_label), ("positive", 1))

    def test_acl_negation(self) -> None:
        result = self.extractor.extract("Findings: No ACL tear.")["ACL"]
        self.assertEqual((result.status, result.derived_label), ("negative", 0))

    def test_acl_uncertainty_is_not_binary(self) -> None:
        result = self.extractor.extract("Possible ACL tear.")["ACL"]
        self.assertEqual(result.status, "uncertain")
        self.assertIsNone(result.derived_label)
        self.assertLess(result.confidence, self.extractor.extract("ACL tear.")["ACL"].confidence)

    def test_absent_target_stays_unknown(self) -> None:
        result = self.extractor.extract("Small joint effusion.")["ACL"]
        self.assertEqual(result.status, "unknown")
        self.assertIsNone(result.derived_label)

    def test_clinical_history_is_not_diagnostic(self) -> None:
        result = self.extractor.extract("Clinical history: suspected ACL tear. Findings: ACL intact.")["ACL"]
        self.assertEqual((result.status, result.derived_label), ("negative", 0))

    def test_reproducible(self) -> None:
        report = "Hallazgos: rotura del menisco medial. Sin derrame articular."
        self.assertEqual(self.extractor.extract(report), self.extractor.extract(report))

    def test_secondary_negation_does_not_cancel_finding(self) -> None:
        result = self.extractor.extract("Lateral meniscus tear without extrusion.")["Lateral Meniscus"]
        self.assertEqual((result.status, result.derived_label), ("positive", 1))

    def test_punctuation_without_space_still_scopes_negation(self) -> None:
        result = self.extractor.extract("Retinacular defect not seen.Fracture of tibial plateau.")["Fracture"]
        self.assertEqual((result.status, result.derived_label), ("positive", 1))


class FullSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        path = Path(__file__).resolve().parents[1] / "data" / "train.csv"
        cls.train = pd.read_csv(path, dtype={"StudyInstanceUID": str})
        cls.supervision = build_supervision(cls.train)

    def test_full_schema_and_cardinality(self) -> None:
        validate_supervision(self.supervision, self.train, expected_studies=4407)
        self.assertEqual(len(self.supervision), 4407 * 12)
        self.assertEqual(self.supervision["StudyInstanceUID"].nunique(), 4407)
        self.assertEqual(set(self.supervision["target"]), set(TARGETS))

    def test_gold_override(self) -> None:
        gold = self.supervision[self.supervision["official_label"].notna()]
        self.assertEqual(len(gold), 58 * 12)
        pd.testing.assert_series_equal(gold["final_label"], gold["official_label"], check_names=False)
        self.assertTrue(gold["final_source"].eq("official").all())

    def test_unresolved_not_silently_negative(self) -> None:
        unresolved = self.supervision[
            self.supervision["status"].isin(["unknown", "uncertain"])
            & self.supervision["official_label"].isna()
        ]
        self.assertTrue(unresolved["final_label"].isna().all())

    def test_declarative_config_matches_executable_policy(self) -> None:
        path = Path(__file__).resolve().parents[1] / "config" / "03_report_label_generation" / "policy_v1.json"
        config = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(tuple(config["targets"]), TARGETS)
        self.assertEqual(config["expected_studies"], 4407)
        self.assertEqual(config["expected_complete_gold_studies"], 58)


if __name__ == "__main__":
    unittest.main()
