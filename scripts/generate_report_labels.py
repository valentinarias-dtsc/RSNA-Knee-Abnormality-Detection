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
from src.report_labels.constants import POLICY_CONFIG_NAME as V2_CONFIG_NAME, POLICY_VERSION as V2_POLICY_VERSION
from src.report_labels.v3.constants import POLICY_CONFIG_NAME as V3_CONFIG_NAME, POLICY_VERSION as V3_POLICY_VERSION
from src.report_labels.v3.pipeline import run_pipeline_v3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", choices=("v2", "v3"), default="v3")
    parser.add_argument("--train", type=Path, default=ROOT / "data" / "train.csv")
    parser.add_argument("--artifact-dir", type=Path, default=ROOT / "artifacts" / "03_report_label_generation")
    parser.add_argument("--figure-dir", type=Path, default=ROOT / "figures" / "03_report_label_generation")
    parser.add_argument("--stage-report", type=Path)
    parser.add_argument("--implementation-report", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--v2-supervision", type=Path, default=ROOT / "artifacts" / "03_report_label_generation" / "supervision_long_v2.csv")
    parser.add_argument("--expected-studies", type=int)
    parser.add_argument("--expected-gold", type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.policy == "v3":
        policy_version, config_name = V3_POLICY_VERSION, V3_CONFIG_NAME
        stage_report = args.stage_report or ROOT / "reports" / "stages" / "03_report_label_generation_v3.md"
        implementation_report = args.implementation_report or ROOT / "reports" / "implementation" / "03_report_label_generation_v3_implementation.md"
    else:
        policy_version, config_name = V2_POLICY_VERSION, V2_CONFIG_NAME
        stage_report = args.stage_report or ROOT / "reports" / "stages" / "03_report_label_generation.md"
        implementation_report = args.implementation_report or ROOT / "reports" / "implementation" / "03_report_label_generation_implementation.md"
    args.config = args.config or ROOT / "config" / "03_report_label_generation" / config_name
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if config["policy_version"] != policy_version:
        raise ValueError("configuration policy version does not match executable policy")
    expected_studies = args.expected_studies or int(config["expected_studies"])
    expected_gold = args.expected_gold or int(config["expected_complete_gold_studies"])
    runner = run_pipeline_v3 if args.policy == "v3" else run_pipeline
    kwargs = dict(
        train_path=args.train,
        artifact_dir=args.artifact_dir,
        figure_dir=args.figure_dir,
        stage_report_path=stage_report,
        implementation_report_path=implementation_report,
        expected_studies=expected_studies,
        expected_gold=expected_gold,
        config_path=args.config,
    )
    if args.policy == "v3":
        kwargs["v2_supervision_path"] = args.v2_supervision
    outputs = runner(**kwargs)
    for name, path in outputs.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
