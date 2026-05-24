from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.beat_battle_agent.battle_result_memory import analyze_battle_results  # noqa: E402


def main() -> int:
    summary = analyze_battle_results(ROOT_DIR)
    print(f"RESULTS_COUNT={summary.get('results_count', 0)}")
    return 0 if summary.get("blocker", "") == "" else 1


if __name__ == "__main__":
    raise SystemExit(main())
