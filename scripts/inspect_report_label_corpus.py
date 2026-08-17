"""Reproduce the descriptive corpus inspection for report-label policy v3."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.report_labels.v3.inspection import InspectionParameters, run_inspection


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, default=ROOT / "data" / "train.csv")
    parser.add_argument(
        "--supervision", type=Path,
        default=ROOT / "artifacts" / "03_report_label_generation" / "supervision_long_v3.csv",
    )
    parser.add_argument(
        "--config", type=Path,
        default=ROOT / "config" / "03_report_label_generation" / "policy_v3.json",
    )
    parser.add_argument(
        "--output-dir", type=Path,
        default=ROOT / "artifacts" / "03_report_label_generation" / "corpus_inspection_v3",
    )
    parser.add_argument(
        "--report", type=Path,
        default=ROOT / "reports" / "stages" / "report_label_v3_corpus_inspection.md",
    )
    parser.add_argument("--expected-studies", type=int)
    parser.add_argument("--seed", type=int, default=20260817)
    parser.add_argument("--audit-sample-max-rows", type=int, default=600)
    parser.add_argument("--similarity-max-pairs-per-stratum", type=int, default=20_000)
    parser.add_argument("--ngram-top-k", type=int, default=100)
    parser.add_argument("--duplicate-group-text-limit", type=int, default=1_000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    expected_studies = args.expected_studies or int(config["expected_studies"])
    parameters = InspectionParameters(
        seed=args.seed,
        audit_sample_max_rows=args.audit_sample_max_rows,
        similarity_max_pairs_per_stratum=args.similarity_max_pairs_per_stratum,
        ngram_top_k=args.ngram_top_k,
        duplicate_group_text_limit=args.duplicate_group_text_limit,
    )
    reviewed_sources = (
        ROOT / "src" / "report_labels" / "text.py",
        ROOT / "src" / "report_labels" / "extraction.py",
        ROOT / "src" / "report_labels" / "v3" / "schema.py",
        ROOT / "src" / "report_labels" / "v3" / "text.py",
        ROOT / "src" / "report_labels" / "v3" / "extraction.py",
        ROOT / "src" / "report_labels" / "v3" / "reconciliation.py",
        ROOT / "src" / "report_labels" / "v3" / "evaluation.py",
        ROOT / "src" / "report_labels" / "v3" / "pipeline.py",
        ROOT / "src" / "report_labels" / "v3" / "inspection.py",
        ROOT / "src" / "report_labels" / "v3" / "inspection_reporting.py",
        ROOT / "scripts" / "generate_report_labels.py",
        ROOT / "scripts" / "inspect_report_label_corpus.py",
        ROOT / "tests" / "test_report_labels_v3.py",
        ROOT / "tests" / "test_report_label_corpus_inspection.py",
        ROOT / "reports" / "stages" / "03_report_label_generation_v3.md",
        ROOT / "reports" / "implementation" / "03_report_label_generation_v3_implementation.md",
    )
    outputs = run_inspection(
        train_path=args.train,
        supervision_path=args.supervision,
        policy_config_path=args.config,
        output_dir=args.output_dir,
        report_path=args.report,
        expected_studies=expected_studies,
        parameters=parameters,
        reviewed_sources=reviewed_sources,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
