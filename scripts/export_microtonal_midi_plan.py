from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.microtonal.microtonal_export_policy import EXPORT_STRATEGIES, build_microtonal_export_plan

REPORT_DIR = ROOT_DIR / "reports" / "microtonal"
PLAN_JSON = REPORT_DIR / "microtonal_export_plan.json"
PLAN_MD = REPORT_DIR / "microtonal_export_plan.md"


def build_export_plan() -> dict:
    return {
        "status": "ok",
        "strategies": [build_microtonal_export_plan(strategy=item, polyphonic=True) for item in EXPORT_STRATEGIES],
        "constraints": {"no_audio_generated": True, "cloud_called": False, "training_performed": False, "ableton_required": False},
    }


def main() -> int:
    payload = build_export_plan()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    PLAN_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    PLAN_MD.write_text("# Microtonal Export Plan\n", encoding="utf-8")
    print(f"MICROTONAL_EXPORT_PLAN_JSON={PLAN_JSON.as_posix()}")
    print(f"MICROTONAL_EXPORT_PLAN_MD={PLAN_MD.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
