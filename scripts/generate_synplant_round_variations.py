from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.beat_battle_agent.agent_config_schema import load_optional_local_agent_config  # noqa: E402
from features.beat_battle_agent.synplant_round_variations import generate_synplant_variations  # noqa: E402


def main() -> int:
    config, blocker = load_optional_local_agent_config(ROOT_DIR)
    if config is None:
        print(f"BLOCKER={blocker}")
        return 1
    result = generate_synplant_variations(ROOT_DIR, config)
    print(f"SYNPLANT_VARIATIONS_OK={str(result.get('ok', False)).lower()}")
    print(f"ROUND_ID={result.get('round_id', '')}")
    if not result.get("ok", False):
        print(f"BLOCKER={result.get('blocker', 'unknown')}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
