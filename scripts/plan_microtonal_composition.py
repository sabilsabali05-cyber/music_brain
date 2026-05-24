from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.microtonal.microtonal_export_policy import EXPORT_STRATEGIES
from features.microtonal.microtonal_ir_adapter import build_microtonal_ir_plan
from features.microtonal.tuning_registry import SUPPORTED_TUNING_PRESETS

REPORT_DIR = ROOT_DIR / "reports" / "microtonal"
PLAN_JSON = REPORT_DIR / "microtonal_composition_plan.json"
PLAN_MD = REPORT_DIR / "microtonal_composition_plan.md"


def build_plan() -> dict:
    selected = "24_edo"
    return {
        "status": "ok",
        "selected_preset": selected,
        "supported_presets": SUPPORTED_TUNING_PRESETS,
        "supported_export_strategies": EXPORT_STRATEGIES,
        "ir_plan": build_microtonal_ir_plan(preset_id=selected, stems=["drums", "bass", "chords", "lead", "texture"]),
        "constraints": {"no_audio_generated": True, "cloud_called": False, "training_performed": False, "ableton_required": False},
    }


def main() -> int:
    payload = build_plan()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    PLAN_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    PLAN_MD.write_text("# Microtonal Composition Plan\n\n- selected_preset: `24_edo`\n", encoding="utf-8")
    print(f"MICROTONAL_PLAN_JSON={PLAN_JSON.as_posix()}")
    print(f"MICROTONAL_PLAN_MD={PLAN_MD.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
