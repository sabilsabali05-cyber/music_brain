from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.beat_battle_agent.round_kit_analysis import analyze_manual_round_kit  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze manually imported Beat Battle round kit.")
    _ = parser.parse_args()
    result = analyze_manual_round_kit(ROOT_DIR)
    if not result.get("ok", False):
        print(f"BLOCKER={result.get('blocker', 'unknown')}")
        return 1
    print(f"ROUND_ID={result.get('round_id', '')}")
    print(f"SOUNDS_COUNT={result.get('sounds_count', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
