from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.beat_battle_agent.agent_config_schema import load_optional_local_agent_config  # noqa: E402
from features.beat_battle_agent.agent_runtime import read_json, write_json, write_markdown  # noqa: E402
from features.beat_battle_agent.agent_state_schema import load_or_default_state, save_state  # noqa: E402
from features.beat_battle_agent.agent_dashboard import build_dashboard  # noqa: E402
from features.beat_battle_agent.battle_draft_ranker import rank_round_drafts  # noqa: E402
from features.beat_battle_agent.round_beat_generator import generate_round_beats  # noqa: E402
from features.beat_battle_agent.round_watcher import update_agent_status, watch_round_once  # noqa: E402
from features.beat_battle_agent.synplant_round_variations import generate_synplant_variations  # noqa: E402
from features.beat_battle_agent.synplant_variation_selector import select_useful_variations  # noqa: E402


def _run(script_name: str, args: list[str] | None = None) -> int:
    cmd = [sys.executable, str(ROOT_DIR / "scripts" / script_name)]
    if args:
        cmd.extend(args)
    result = subprocess.run(cmd, cwd=ROOT_DIR, check=False)
    return result.returncode


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one Beat Battle agent iteration.")
    parser.add_argument("--manual-submit-confirmed", action="store_true")
    args = parser.parse_args()
    config, blocker = load_optional_local_agent_config(ROOT_DIR)
    if config is None:
        print(f"BLOCKER={blocker}")
        return 1
    state_path = ROOT_DIR / config.paths.local_state_path
    state = load_or_default_state(state_path)
    watch_payload = watch_round_once(ROOT_DIR, config)
    round_id = str(watch_payload.get("active_round_id", "")).strip()
    if not round_id:
        update_agent_status(ROOT_DIR, config, {"once_status": "blocked_no_round"})
        return 1
    _run("acquire_beat_battle_round_sounds.py")
    acquisition = read_json(ROOT_DIR / "reports" / "beat_battle_site_automation" / "sound_acquisition_report.json")
    state.sounds_acquired += int(acquisition.get("acquired_count", 0))
    generate_synplant_variations(ROOT_DIR, config)
    select_useful_variations(ROOT_DIR, config, round_id)
    generate_round_beats(ROOT_DIR, config, round_id)
    ranked = rank_round_drafts(ROOT_DIR, round_id)
    state.submission_attempted = False
    state.submitted = False
    submission_attempted = False
    submitted = False
    if state.last_submission_round_id == round_id:
        state.blockers = ["duplicate_round_submission_blocked"]
    elif config.submission_allowed and config.safety.auto_submit and args.manual_submit_confirmed:
        submission_attempted = True
        state.submission_attempted = True
        submit_code = _run("submit_beat_battle_entry.py", ["--manual-submit-confirmed"])
        submit_payload = read_json(ROOT_DIR / "reports" / "beat_battle_site_automation" / "submission_report.json")
        submitted = bool(submit_payload.get("submitted", False)) and submit_code == 0
        state.submitted = submitted
        if submitted:
            state.last_submission_round_id = round_id
    _run("check_beat_battle_result.py")
    result_payload = read_json(ROOT_DIR / "reports" / "beat_battle_site_automation" / "result_report.json")
    result_available = bool(result_payload.get("result_available", False))
    state.result_logged = result_available
    if result_available:
        _append_jsonl(
            ROOT_DIR / config.paths.results_dataset_jsonl_path,
            {
                "result_id": f"{round_id}_result",
                "round_id": round_id,
                "submitted": submitted,
                "result_logged": True,
                "placement": result_payload.get("placement"),
                "score": result_payload.get("score"),
                "source_authorized_for_learning": True,
                "authorization_status": "authorized",
            },
        )
    save_state(state_path, state)
    payload = {
        "round_id": round_id,
        "submission_attempted": submission_attempted,
        "submitted": submitted,
        "result_logged": result_available,
        "ranked_count": int(ranked.get("ranked_count", 0)),
        "auto_submit_enabled": bool(config.safety.auto_submit),
        "manual_confirmation_received": bool(args.manual_submit_confirmed),
        "blocker": ",".join(state.blockers),
    }
    write_json(ROOT_DIR / "reports" / "beat_battle_agent" / "beat_battle_agent_once.json", payload)
    write_markdown(ROOT_DIR / "reports" / "beat_battle_agent" / "beat_battle_agent_once.md", "Beat Battle Agent Once", payload)
    update_agent_status(ROOT_DIR, config, payload)
    build_dashboard(ROOT_DIR, config)
    print(f"ROUND_ID={round_id}")
    print(f"SUBMITTED={str(submitted).lower()}")
    return 0 if payload["blocker"] == "" else 1


if __name__ == "__main__":
    raise SystemExit(main())
