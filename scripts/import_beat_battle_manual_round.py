from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.beat_battle_agent.manual_round_import import import_manual_round  # noqa: E402


def main() -> int:
    result = import_manual_round(ROOT_DIR)
    if not result.get("ok", False):
        print(f"BLOCKER={result.get('blocker', 'unknown')}")
        print("SOUNDS_IMPORTED=0")
        return 1
    print(f"ROUND_ID={result.get('round_id', '')}")
    print(f"SOUNDS_IMPORTED={result.get('sounds_imported', 0)}")
    print(f"MANIFEST_PATH={result.get('manifest_path', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
