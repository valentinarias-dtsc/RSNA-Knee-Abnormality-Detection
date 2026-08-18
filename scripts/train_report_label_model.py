"""Prepare, train and evaluate the Stage 04 report-label baseline."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.report_label_model.pipeline import prepare_stage04, run_full_stage04, run_smoke_stage04


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "config" / "04_report_label_model" / "baseline_xlmr_v1.json",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--prepare-only", action="store_true", help="Build datasets/splits without model dependencies.")
    mode.add_argument("--smoke-test", action="store_true", help="Run a tiny non-official model I/O check.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = args.config if args.config.is_absolute() else ROOT / args.config
    if args.prepare_only:
        outputs = prepare_stage04(ROOT, config_path)
        status = "Stage 04 preparation complete (no model metrics produced)."
    elif args.smoke_test:
        outputs = run_smoke_stage04(ROOT, config_path)
        status = "Stage 04 smoke test complete (not official Stage 04 metrics)."
    else:
        outputs = run_full_stage04(ROOT, config_path)
        status = "Stage 04 training and weak-label evaluation complete."
    print(status)
    print(f"artifact_dir: {outputs['paths']['artifact_dir']}")
    print(f"figure_dir: {outputs['paths']['figure_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
