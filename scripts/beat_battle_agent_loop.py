from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.beat_battle_agent.agent_config_schema import load_optional_local_agent_config  # noqa: E402
from features.beat_battle_agent.agent_runtime import write_json, write_markdown  # noqa: E402
from features.beat_battle_agent.agent_dashboard import build_dashboard  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Beat Battle continuous loop.")
    parser.add_argument("--iterations", type=int, default=1)
    args = parser.parse_args()
    config, blocker = load_optional_local_agent_config(ROOT_DIR)
    if config is None:
        print(f"BLOCKER={blocker}")
        return 1
    iterations = max(1, min(args.iterations, config.max_rounds_per_loop))
    rounds_processed = 0
    last_code = 0
    for idx in range(iterations):
        cmd = [sys.executable, str(ROOT_DIR / "scripts" / "beat_battle_agent_once.py")]
        last_code = subprocess.run(cmd, cwd=ROOT_DIR, check=False).returncode
        once_payload_path = ROOT_DIR / "reports" / "beat_battle_agent" / "beat_battle_agent_once.json"
        if once_payload_path.exists():
            payload = json.loads(once_payload_path.read_text(encoding="utf-8"))
            if str(payload.get("round_id", "")).strip():
                rounds_processed += 1
        if idx < iterations - 1:
            time.sleep(config.poll_interval_seconds)
    report = {
        "iterations_requested": args.iterations,
        "iterations_ran": iterations,
        "rounds_processed": rounds_processed,
        "last_exit_code": last_code,
    }
    write_json(ROOT_DIR / "reports" / "beat_battle_agent" / "beat_battle_agent_loop.json", report)
    write_markdown(ROOT_DIR / "reports" / "beat_battle_agent" / "beat_battle_agent_loop.md", "Beat Battle Agent Loop", report)
    build_dashboard(ROOT_DIR, config, {"loop_iterations_ran": iterations})
    print(f"ROUNDS_PROCESSED={rounds_processed}")
    return 0 if last_code == 0 else last_code


if __name__ == "__main__":
    raise SystemExit(main())
