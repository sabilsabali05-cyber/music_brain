from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.beat_battle_agent.battle_result_memory import ingest_local_battle_result  # noqa: E402


def main() -> int:
    result = ingest_local_battle_result(ROOT_DIR)
    if not result.get("ok", False):
        print(f"BLOCKER={result.get('blocker', 'unknown')}")
        return 1
    print(f"BATTLE_RESULTS_PATH={result.get('battle_results_path', '')}")
    print(f"SITE_FEEDBACK_PATH={result.get('feedback_path', '')}")
    print(f"ROWS_WRITTEN={result.get('rows_written', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
