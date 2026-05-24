from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.beat_battle_agent.agent_config_schema import load_optional_local_agent_config  # noqa: E402
from features.beat_battle_agent.round_beat_generator import generate_round_beats  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate beat drafts for active round.")
    parser.add_argument("--round-id", default="", help="Optional round id override.")
    args = parser.parse_args()
    config, blocker = load_optional_local_agent_config(ROOT_DIR)
    if config is None:
        print(f"BLOCKER={blocker}")
        return 1
    round_id = str(args.round_id or "").strip()
    if not round_id:
        status_path = ROOT_DIR / config.paths.round_watcher_status_json_path
        if status_path.exists():
            import json

            payload = json.loads(status_path.read_text(encoding="utf-8"))
            round_id = str(payload.get("active_round_id", "")).strip()
    if not round_id:
        print("BLOCKER=missing_round_id")
        return 1
    result = generate_round_beats(ROOT_DIR, config, round_id)
    print(f"DRAFTS_GENERATED={result.get('drafts_generated', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
