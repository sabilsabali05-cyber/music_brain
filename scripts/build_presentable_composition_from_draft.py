from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.composition_projects import run_full_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full presentable composition pipeline.")
    parser.add_argument("--config", default="", help="Optional local config override path.")
    parser.add_argument("--include-reaper", action="store_true", help="Build optional reaper/render pack plan.")
    args = parser.parse_args()
    summary = run_full_pipeline(Path(args.config) if args.config else None, include_reaper=args.include_reaper)
    print(f"PIPELINE_STATUS={summary.get('status', 'unknown')}")
    print(f"CANDIDATES_GENERATED={summary.get('candidates_generated', 0)}")
    print(f"SELECTED_CANDIDATE={summary.get('selected_candidate', 'none')}")
    print(f"SELECTED_FULL_MIDI={summary.get('selected_full_midi_path', '')}")
    print(f"SELECTED_STEMS_PATH={summary.get('selected_stems_path', '')}")
    print(f"PRESENTABILITY_SCORE={summary.get('presentability_score', 0.0)}")
    print(f"RATIO_COMPLIANCE_SCORE={summary.get('ratio_compliance_score', 0.0)}")
    print(f"DATABASE_COMPARISON_CONFIDENCE={summary.get('database_comparison_confidence', 0.0)}")
    print(f"SUMMARY_JSON={json.dumps(summary, ensure_ascii=True)}")
    return 0 if summary.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
