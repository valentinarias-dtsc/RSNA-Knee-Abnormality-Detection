from __future__ import annotations

import unittest
import json
from pathlib import Path

import pandas as pd

from src.report_labels.constants import POLICY_VERSION, TARGETS
from src.report_labels.evaluation import audit_supervision_consistency
from src.report_labels.extraction import ReportLabelExtractor
from src.report_labels.pipeline import build_supervision, validate_supervision
from src.report_labels.text import segment_report


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

    def test_header_word_inside_finding_does_not_change_section(self) -> None:
        report = (
            "Hallazgos:\nAdelgazamiento del LCA, correlacionar con antecedentes regionales.\n"
            "No hay derrame articular."
        )
        result = self.extractor.extract(report)["Effusion"]
        self.assertEqual((result.status, result.derived_label), ("negative", 0))

    def test_reproducible(self) -> None:
        report = "Hallazgos: rotura del menisco medial. Sin derrame articular."
        self.assertEqual(self.extractor.extract(report), self.extractor.extract(report))

    def test_secondary_negation_does_not_cancel_finding(self) -> None:
        result = self.extractor.extract("Lateral meniscus tear without extrusion.")["Lateral Meniscus"]
        self.assertEqual((result.status, result.derived_label), ("positive", 1))

    def test_negated_second_pathology_does_not_cancel_first(self) -> None:
        result = self.extractor.extract(
            "Mild degeneration of the medial meniscus but no tears."
        )["Medial Meniscus"]
        self.assertEqual((result.status, result.derived_label), ("positive", 1))

    def test_punctuation_without_space_still_scopes_negation(self) -> None:
        result = self.extractor.extract("Retinacular defect not seen.Fracture of tibial plateau.")["Fracture"]
        self.assertEqual((result.status, result.derived_label), ("positive", 1))

    def test_collective_ligament_normality_propagates_negative(self) -> None:
        results = self.extractor.extract("Ligamentos cruzados y colaterales de grosor y señal normales.")
        self.assertEqual((results["ACL"].status, results["ACL"].derived_label), ("negative", 0))
        self.assertEqual((results["MCL"].status, results["MCL"].derived_label), ("negative", 0))

    def test_ambiguous_collective_ligament_injury_stays_unknown(self) -> None:
        result = self.extractor.extract("Tears of the cruciate ligaments.")["ACL"]
        self.assertEqual(result.status, "unknown")
        self.assertIsNone(result.derived_label)

    def test_both_menisci_normality_propagates_negative(self) -> None:
        results = self.extractor.extract("Both menisci are intact.")
        for target in ("Medial Meniscus", "Lateral Meniscus"):
            self.assertEqual((results[target].status, results[target].derived_label), ("negative", 0))
            self.assertLess(results[target].confidence, 0.85)

    def test_explicit_both_menisci_pathology_propagates_positive(self) -> None:
        results = self.extractor.extract("Tears involve both menisci.")
        for target in ("Medial Meniscus", "Lateral Meniscus"):
            self.assertEqual((results[target].status, results[target].derived_label), ("positive", 1))
            self.assertLess(results[target].confidence, 0.90)

    def test_tibiofemoral_collective_normality_propagates_oa_negative(self) -> None:
        results = self.extractor.extract("Cartílago de compartimentos femorotibiales de grosor y señal normal.")
        for target in ("Medial OA", "Lateral OA"):
            self.assertEqual((results[target].status, results[target].derived_label), ("negative", 0))

    def test_postposed_turkish_negation(self) -> None:
        result = self.extractor.extract("Eklem sivisi saptanmamistir.")["Effusion"]
        self.assertEqual((result.status, result.derived_label), ("negative", 0))

    def test_plural_baker_term(self) -> None:
        result = self.extractor.extract("No hay quistes poplíteos.")["Baker's"]
        self.assertEqual((result.status, result.derived_label), ("negative", 0))

    def test_structured_plural_heading_inherits_following_negation(self) -> None:
        result = self.extractor.extract("CONSTATATIONS :\nFractures :\nAucune.")["Fracture"]
        self.assertEqual((result.status, result.derived_label), ("negative", 0))

    def test_high_confidence_line_wrap_is_joined(self) -> None:
        clauses = segment_report("Menisco medial de morfología normal,\ninespecífico.\nNo hay derrame.")
        self.assertIn("normal, inespecifico", clauses[0].text)
        self.assertEqual(len(clauses), 2)

    def test_audited_spanish_report_target_values(self) -> None:
        report = """Antecedentes Clínicos:
Condromalacia rotuliana.
Hallazgos:
No hay alteraciones difusas de señal de la médula ósea.
Ligamentos cruzados y colaterales de grosor y señal normales.
Menisco medial de morfología normal, con discreto edema de la unión meniscocapsular,
inespecífico.
Menisco lateral de morfología y señal normal, sin signos de rotura.
Cartílago de compartimentos femorotibiales y patelofemoral de grosor y señal normal.
No hay derrame articular. No hay quistes poplíteos.
Impresión:
Leve tendinosis patelar proximal."""
        results = self.extractor.extract(report)
        expected = {
            "ACL": 0, "MCL": 0, "Medial Meniscus": 0, "Lateral Meniscus": 0,
            "Medial OA": 0, "Lateral OA": 0, "PF OA": 0, "Effusion": 0,
            "Synovitis": None, "Baker's": 0, "Contusion": None, "Fracture": None,
        }
        self.assertEqual({target: results[target].derived_label for target in TARGETS}, expected)

    def test_audited_south_slavic_report_target_values(self) -> None:
        report = """Na seriji MR presjeka lijevog koljena nalazi se kompleksna, predominantno horizontala ruptura
prednjeg roga, trupa i stražnjeg roga medijalnog meniska.
Lateralni menisk je primjerene morfologije i intenziteta signala.
Blaža mukoidna degeneracija prednjeg križnog ligamenta, bez znakova rupture.
Lezija I. stupnja medijalnog kolateralnog ligamenta."""
        results = self.extractor.extract(report)
        expected = {
            "ACL": 1,
            "MCL": 1,
            "Medial Meniscus": 1,
            "Lateral Meniscus": 0,
        }
        self.assertEqual({target: results[target].derived_label for target in expected}, expected)

    def test_decisive_evidence_is_persisted_before_conflict(self) -> None:
        result = self.extractor.extract("ACL intact. ACL intact. ACL intact. ACL tear.")["ACL"]
        self.assertEqual(result.status, "positive")
        self.assertIn("tear", result.evidence[0])
        self.assertIn("conflict", result.rationale)

    def test_same_clause_normality_and_pathology_is_not_artificial_conflict(self) -> None:
        result = self.extractor.extract("ACL intact with mucoid degeneration.")["ACL"]
        self.assertEqual(result.status, "positive")
        self.assertEqual(result.rationale, "explicit positive evidence")

    def test_pathology_is_scoped_to_nearest_anatomy(self) -> None:
        result = self.extractor.extract(
            "Medial meniscus tear displaced into the gutter adjacent to the MCL."
        )["MCL"]
        self.assertEqual(result.status, "unknown")

    def test_structured_semicolon_keeps_mcl_finding(self) -> None:
        result = self.extractor.extract("MCL:\n  deep MCL; high grade partial tear")["MCL"]
        self.assertEqual((result.status, result.derived_label), ("positive", 1))

    def test_posterior_cruciate_normality_does_not_negate_acl(self) -> None:
        result = self.extractor.extract("Arka çapraz ve yan bağlar normal.")["ACL"]
        self.assertEqual(result.status, "unknown")


class FullSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        path = Path(__file__).resolve().parents[1] / "data" / "train.csv"
        cls.train = pd.read_csv(path, dtype={"StudyInstanceUID": str})
        cls.supervision = build_supervision(cls.train)
        cls.audit_summary, cls.audit_issues = audit_supervision_consistency(cls.supervision, cls.train)

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
        path = Path(__file__).resolve().parents[1] / "config" / "03_report_label_generation" / "policy_v2.json"
        config = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(config["policy_version"], POLICY_VERSION)
        self.assertEqual(config["artifact_version"], "v2")
        self.assertEqual(tuple(config["targets"]), TARGETS)
        self.assertEqual(config["expected_studies"], 4407)
        self.assertEqual(config["expected_complete_gold_studies"], 58)

    def test_exhaustive_consistency_audit(self) -> None:
        self.assertEqual(int(self.audit_summary["evaluated_rows"].max()), 4407 * 12)
        self.assertTrue(self.audit_issues.empty, self.audit_issues.head(10).to_dict("records"))


if __name__ == "__main__":
    unittest.main()
