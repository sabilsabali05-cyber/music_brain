from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.microtonal.scala_scl import parse_scl_text
from features.microtonal.tuning_registry import SUPPORTED_TUNING_PRESETS, get_tuning_preset


def main() -> int:
    for preset in SUPPORTED_TUNING_PRESETS:
        get_tuning_preset(preset)
    parsed = parse_scl_text("! x\nDemo\n3\n100.0\n3/2\n700.0\n")
    if not parsed.valid:
        return 1
    print("MICROTONAL_TUNING_VALIDATION=ok")
    print(f"SUPPORTED_PRESET_COUNT={len(SUPPORTED_TUNING_PRESETS)}")
    print("SCALA_PARSE_VALID=True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
