"""Command-line entry point for stage 03 report-derived supervision."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.report_labels.pipeline import run_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, default=ROOT / "data" / "train.csv")
    parser.add_argument("--artifact-dir", type=Path, default=ROOT / "artifacts" / "03_report_label_generation")
    parser.add_argument("--figure-dir", type=Path, default=ROOT / "figures" / "03_report_label_generation")
    parser.add_argument("--stage-report", type=Path, default=ROOT / "reports" / "stages" / "03 - report label generation.md")
    parser.add_argument("--implementation-report", type=Path, default=ROOT / "reports" / "implementation" / "03 - report label generation implementation.md")
    parser.add_argument("--config", type=Path, default=ROOT / "config" / "03_report_label_generation" / "policy_v1.json")
    parser.add_argument("--expected-studies", type=int)
    parser.add_argument("--expected-gold", type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if config["policy_version"] != "report-label-policy-v1.0.0":
        raise ValueError("configuration policy version does not match executable policy")
    expected_studies = args.expected_studies or int(config["expected_studies"])
    expected_gold = args.expected_gold or int(config["expected_complete_gold_studies"])
    outputs = run_pipeline(
        train_path=args.train,
        artifact_dir=args.artifact_dir,
        figure_dir=args.figure_dir,
        stage_report_path=args.stage_report,
        implementation_report_path=args.implementation_report,
        expected_studies=expected_studies,
        expected_gold=expected_gold,
        config_path=args.config,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
