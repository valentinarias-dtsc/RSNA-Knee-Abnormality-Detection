from __future__ import annotations

import json
from pathlib import Path
import unittest

import pandas as pd

from src.report_labels.constants import TARGETS
from src.report_labels.pipeline import validate_supervision
from src.report_labels.v3.constants import POLICY_VERSION
from src.report_labels.v3.evaluation import audit_supervision_v3, exact_template_consistency
from src.report_labels.v3.extraction import V3ReportLabelExtractor
from src.report_labels.v3.pipeline import build_supervision_v3
from src.report_labels.v3.text import build_text_views


class V3ExtractionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.extractor = V3ReportLabelExtractor()

    def test_absent_target_remains_unknown(self) -> None:
        result = self.extractor.extract("Findings: small joint effusion.")["Synovitis"]
        self.assertEqual(result.status, "unknown")
        self.assertIsNone(result.derived_label)
        self.assertEqual(result.evidence_provenance, ())

    def test_generic_marrow_edema_is_not_contusion(self) -> None:
        result = self.extractor.extract(
            "Findings: subchondral bone marrow edema in the medial femoral condyle."
        )["Contusion"]
        self.assertEqual(result.status, "unknown")

    def test_synovial_cyst_is_not_synovitis(self) -> None:
        result = self.extractor.extract(
            "Findings: perisynovial cyst. No other abnormality."
        )["Synovitis"]
        self.assertEqual(result.status, "unknown")

    def test_turkish_effusion_inflection(self) -> None:
        result = self.extractor.extract(
            "Bulgular: Eklem mesafesinde hafif efüzyon izlenmiştir."
        )["Effusion"]
        self.assertEqual((result.status, result.derived_label), ("positive", 1))
        self.assertIn("v3_morphology", result.detectors)

    def test_turkish_postposed_effusion_negation(self) -> None:
        result = self.extractor.extract(
            "Bulgular: Eklemde sıvı artışı saptanmamıştır."
        )["Effusion"]
        self.assertEqual((result.status, result.derived_label), ("negative", 0))

    def test_south_slavic_baker_variant(self) -> None:
        result = self.extractor.extract("Nalaz: Sitna Baker cista.")["Baker's"]
        self.assertEqual((result.status, result.derived_label), ("positive", 1))

    def test_german_synovial_proliferation(self) -> None:
        result = self.extractor.extract(
            "Befund: Gelenkerguss mit verdickter Synovia und synovialen Proliferationen."
        )["Synovitis"]
        self.assertEqual((result.status, result.derived_label), ("positive", 1))

    def test_french_fracture_derivative_negation(self) -> None:
        result = self.extractor.extract(
            "Constatations: Il n'y a pas de trait fracturaire."
        )["Fracture"]
        self.assertEqual((result.status, result.derived_label), ("negative", 0))

    def test_dutch_medial_oa_morphology(self) -> None:
        result = self.extractor.extract(
            "Bevindingen: Denudatie van het kraakbeen mediaal femorotibiaal met osteofyten."
        )["Medial OA"]
        self.assertEqual((result.status, result.derived_label), ("positive", 1))
        self.assertIn("chondral_abnormality", result.phenotypes)

    def test_coordinated_tibiofemoral_oa_reaches_both_targets(self) -> None:
        results = self.extractor.extract(
            "Findings: Mild to moderate medial and lateral femorotibial chondrosis."
        )
        for target in ("Medial OA", "Lateral OA"):
            self.assertEqual((results[target].status, results[target].derived_label), ("positive", 1))

    def test_negated_cartilage_defect_is_negative(self) -> None:
        result = self.extractor.extract(
            "Findings: lateral compartment cartilage: no focal cartilage defects."
        )["Lateral OA"]
        self.assertEqual((result.status, result.derived_label), ("negative", 0))

    def test_normal_patellofemoral_ligament_does_not_resolve_pf_oa(self) -> None:
        result = self.extractor.extract(
            "Findings: medial patellofemoral ligament and patellar retinacula are normal."
        )["PF OA"]
        self.assertEqual(result.status, "unknown")

    def test_pathology_competes_between_menisci(self) -> None:
        results = self.extractor.extract(
            "Bulgular: Lateral menisküste grade I dejenerasyon, medial menisküste grade III dejenerasyon ve yırtık."
        )
        self.assertEqual(results["Medial Meniscus"].derived_label, 1)
        self.assertEqual(results["Lateral Meniscus"].derived_label, 1)

    def test_negated_tear_does_not_hide_explicit_degeneration_phenotype(self) -> None:
        result = self.extractor.extract(
            "Nalaz: Degenerativno promijenjen lateralni menisk, bez znakova rupture."
        )["Lateral Meniscus"]
        self.assertEqual((result.status, result.derived_label), ("positive", 1))
        self.assertEqual(result.phenotypes[0], "degeneration")

    def test_locative_mcl_reference_does_not_become_injury(self) -> None:
        result = self.extractor.extract(
            "Findings: Medial meniscus tear displaced into the gutter adjacent to the MCL."
        )["MCL"]
        self.assertEqual(result.status, "unknown")

    def test_south_slavic_locative_mcl_reference_does_not_become_injury(self) -> None:
        result = self.extractor.extract(
            "Nalaz: Kompleksna ruptura stražnjeg roga medijalnog mensika koji blago ekstrudira pod MCL."
        )["MCL"]
        self.assertEqual(result.status, "unknown")

    def test_lesion_anterior_to_meniscus_does_not_become_meniscal_injury(self) -> None:
        result = self.extractor.extract(
            "Findings: a stable cystic lesion anterior to the lateral meniscus. Lateral meniscus intact."
        )["Lateral Meniscus"]
        self.assertEqual((result.status, result.derived_label), ("negative", 0))

    def test_lesion_in_front_of_acl_does_not_become_acl_injury(self) -> None:
        result = self.extractor.extract(
            "Findings: a cystic lesion in front of the ACL. ACL is intact."
        )["ACL"]
        self.assertEqual((result.status, result.derived_label), ("negative", 0))

    def test_trochlear_cartilage_loss_is_pf_not_medial_oa(self) -> None:
        results = self.extractor.extract(
            "Findings: preserved medial and lateral tibiofemoral cartilage; focal cartilage loss at the femoral trochlea."
        )
        self.assertEqual(results["Medial OA"].derived_label, 0)
        self.assertEqual(results["Lateral OA"].derived_label, 0)
        self.assertEqual(results["PF OA"].derived_label, 1)

    def test_provenance_matches_selected_evidence(self) -> None:
        result = self.extractor.extract("Findings: ACL tear.")["ACL"]
        self.assertEqual(result.evidence[0], result.evidence_provenance[0]["evidence"])
        self.assertEqual(result.status, result.evidence_provenance[0]["status"])
        self.assertIn("v3_target", result.detectors)

    def test_linked_views_require_structural_cue(self) -> None:
        unlinked = build_text_views("ACL intact. Patellar tendinosis.")
        self.assertFalse(any(view.kind == "linked" for view in unlinked))


class V3SchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        records = []
        for uid, report in (("one", "Findings: ACL tear."), ("two", "Findings: ACL tear.")):
            record = {"StudyInstanceUID": uid, "Report": report}
            record.update({target: pd.NA for target in TARGETS})
            records.append(record)
        self.train = pd.DataFrame(records)
        self.supervision = build_supervision_v3(self.train)

    def test_small_schema_and_unknown_policy(self) -> None:
        validate_supervision(self.supervision, self.train, expected_studies=2)
        self.assertEqual(len(self.supervision), 2 * len(TARGETS))
        unknown = self.supervision[self.supervision["status"].eq("unknown")]
        self.assertTrue(unknown["derived_label"].isna().all())
        self.assertTrue(unknown["evidence"].eq("[]").all())

    def test_v3_audit_and_exact_template_consistency(self) -> None:
        summary, issues = audit_supervision_v3(self.supervision, self.train)
        self.assertTrue(issues.empty, issues.to_dict("records"))
        self.assertTrue(summary["passed"].all())
        templates = exact_template_consistency(self.train, self.supervision)
        self.assertEqual(int(templates["inconsistent_targets"].sum()), 0)
        self.assertEqual(set(templates["template_mode"]), {"exact", "numeric_normalized"})

    def test_declarative_policy_matches_executable(self) -> None:
        path = Path(__file__).resolve().parents[1] / "config" / "03_report_label_generation" / "policy_v3.json"
        config = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(config["policy_version"], POLICY_VERSION)
        self.assertEqual(config["artifact_version"], "v3")
        self.assertEqual(tuple(config["targets"]), TARGETS)
        self.assertEqual(config["missing_mention_policy"], "unknown")
        self.assertEqual(config["expected_complete_gold_studies"], 58)


if __name__ == "__main__":
    unittest.main()
