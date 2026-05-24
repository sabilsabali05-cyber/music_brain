from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.beat_battle_agent.agent_config_schema import load_optional_local_agent_config  # noqa: E402
from features.beat_battle_agent.round_watcher import update_agent_status, watch_round_once  # noqa: E402


def main() -> int:
    config, blocker = load_optional_local_agent_config(ROOT_DIR)
    if config is None:
        print(f"BLOCKER={blocker}")
        return 1
    payload = watch_round_once(ROOT_DIR, config)
    update_agent_status(ROOT_DIR, config, {"watcher_last_blocker": payload.get("blocker", "")})
    print(f"ROUND_WATCHER_STATUS_JSON={config.paths.round_watcher_status_json_path}")
    return 0 if payload.get("active_round_detected") else 1


if __name__ == "__main__":
    raise SystemExit(main())
