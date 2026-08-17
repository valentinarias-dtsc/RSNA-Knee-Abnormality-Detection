from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from src.report_labels.constants import TARGETS
from src.report_labels.v3.inspection import (
    InspectionParameters,
    build_inspection_frames,
    run_inspection,
)
from src.report_labels.v3.pipeline import build_supervision_v3


class ReportLabelCorpusInspectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        reports = [
            ("study-a", "Findings: ACL tear. No joint effusion. Both menisci are normal."),
            ("study-b", "Findings: ACL tear grade 1. Small Baker cyst."),
            ("study-c", "Findings: ACL tear grade 2. Small Baker cyst."),
        ]
        rows = []
        for uid, report in reports:
            row = {"StudyInstanceUID": uid, "Report": report}
            row.update({target: pd.NA for target in TARGETS})
            rows.append(row)
        cls.train = pd.DataFrame(rows)
        cls.supervision = build_supervision_v3(cls.train)
        cls.parameters = InspectionParameters(
            seed=17,
            audit_sample_max_rows=50,
            similarity_max_pairs_per_stratum=100,
            ngram_top_k=10,
            duplicate_group_text_limit=200,
        )

    def test_semantic_outputs_are_deterministic(self) -> None:
        first, first_diagnostics = build_inspection_frames(
            self.train, self.supervision, self.parameters, expected_studies=3,
        )
        second, second_diagnostics = build_inspection_frames(
            self.train, self.supervision, self.parameters, expected_studies=3,
        )
        self.assertEqual(first_diagnostics, second_diagnostics)
        self.assertEqual(set(first), set(second))
        for key in first:
            pd.testing.assert_frame_equal(first[key], second[key], check_dtype=True)

    def test_cardinalities_and_denominators_reconcile(self) -> None:
        frames, diagnostics = build_inspection_frames(
            self.train, self.supervision, self.parameters, expected_studies=3,
        )
        self.assertEqual(diagnostics["studies"], 3)
        self.assertEqual(diagnostics["study_target_pairs"], 3 * len(TARGETS))
        target = frames["target_status_summary"]
        self.assertTrue(target["pairs"].eq(3).all())
        self.assertTrue(
            target[["positive", "negative", "uncertain", "unknown"]].sum(axis=1).eq(target["pairs"]).all()
        )
        self.assertEqual(len(frames["study_level_distribution"]), 3)
        self.assertEqual(set(frames["study_level_distribution"]["StudyInstanceUID"]), {"study-a", "study-b", "study-c"})

    def test_audit_rows_trace_to_source(self) -> None:
        frames, _ = build_inspection_frames(
            self.train, self.supervision, self.parameters, expected_studies=3,
        )
        sample = frames["audit_sample"]
        self.assertFalse(sample.empty)
        self.assertTrue(set(sample["StudyInstanceUID"]).issubset(set(self.train["StudyInstanceUID"])))
        source_reports = self.train.set_index("StudyInstanceUID")["Report"]
        self.assertTrue(all(row.Report == source_reports.loc[row.StudyInstanceUID] for row in sample.itertuples()))
        self.assertTrue(sample["judgment"].eq("").all())

    def test_template_and_provenance_joins_reconcile(self) -> None:
        frames, diagnostics = build_inspection_frames(
            self.train, self.supervision, self.parameters, expected_studies=3,
        )
        templates = frames["template_family_summary"]
        self.assertEqual(set(templates["template_mode"]), {"exact", "numeric_normalized"})
        numeric_duplicates = templates[
            templates["template_mode"].eq("numeric_normalized") & templates["is_duplicated_family"]
        ]
        self.assertGreaterEqual(len(numeric_duplicates), 1)
        self.assertEqual(
            diagnostics["selected_evidence_entries"],
            len(frames["evidence_inventory"]),
        )
        self.assertEqual(
            diagnostics["selected_winning_evidence_entries"],
            int(frames["evidence_inventory"]["is_winning_status"].sum()),
        )
        collective = frames["collective_evidence_summary"]
        self.assertTrue(collective.loc[collective["record_type"].eq("mention"), "propositions"].eq(0).all())
        self.assertTrue(collective.loc[collective["record_type"].eq("proposition"), "mentions"].eq(0).all())
        detector_overall = frames["detector_summary"]
        detector_overall = detector_overall[detector_overall["target"].eq("__all__")]
        self.assertFalse(detector_overall.duplicated(["unit", "detector"]).any())

    def test_entrypoint_outputs_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            train_path = root / "train.csv"
            supervision_path = root / "supervision.csv"
            config_path = root / "policy.json"
            output_dir = root / "inspection"
            report_path = root / "report.md"
            self.train.to_csv(train_path, index=False)
            self.supervision.to_csv(supervision_path, index=False)
            config_path.write_text(json.dumps({"policy_version": "report-label-policy-v3.0.0"}), encoding="utf-8")
            outputs = run_inspection(
                train_path=train_path,
                supervision_path=supervision_path,
                policy_config_path=config_path,
                output_dir=output_dir,
                report_path=report_path,
                expected_studies=3,
                parameters=self.parameters,
            )
            self.assertTrue(outputs["metadata"].exists())
            self.assertTrue(outputs["report"].exists())
            metadata = json.loads(outputs["metadata"].read_text(encoding="utf-8"))
            self.assertEqual(metadata["counts"]["studies"], 3)
            self.assertEqual(metadata["counts"]["study_target_pairs"], 36)
            self.assertEqual(metadata["policy_version"], "report-label-policy-v3.0.0")
            for key, detail in metadata["outputs"].items():
                self.assertIn("sha256", detail, key)


if __name__ == "__main__":
    unittest.main()
