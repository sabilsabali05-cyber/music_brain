from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.beat_battle_agent.synplant_study_catalog import generate_synplant_study_catalog  # noqa: E402


def main() -> int:
    result = generate_synplant_study_catalog(ROOT_DIR)
    if not result.get("ok", False):
        print(f"BLOCKER={result.get('blocker', 'unknown')}")
        print("SYNPLANT_STUDY_VARIATIONS_GENERATED=0")
        return 1
    print(f"ROUND_ID={result.get('round_id', '')}")
    print(f"SYNPLANT_STUDY_VARIATIONS_GENERATED={result.get('variations_generated', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
