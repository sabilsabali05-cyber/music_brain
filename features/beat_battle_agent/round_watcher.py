from __future__ import annotations

from pathlib import Path
from typing import Any

from .agent_config_schema import BeatBattleAgentConfig
from .agent_runtime import detect_round_status, utc_now, write_json, write_markdown
from .agent_state_schema import BeatBattleAgentState, load_or_default_state, save_state


def watch_round_once(project_root: Path, config: BeatBattleAgentConfig) -> dict[str, Any]:
    state_path = project_root / config.paths.local_state_path
    state = load_or_default_state(state_path)
    detection = detect_round_status(project_root, config)
    round_id = str(detection.get("active_round_id", "")).strip()
    duplicate_round = bool(round_id and round_id in state.rounds_seen)
    if round_id and not duplicate_round:
        state.rounds_seen.append(round_id)
    state.active_round_detected = bool(detection.get("active_round_detected", False))
    state.active_round_id = round_id
    if state.active_round_detected and not duplicate_round:
        state.rounds_processed += 1
    blocker = str(detection.get("blocker", "")).strip()
    if blocker:
        state.blockers = [blocker]
    save_state(state_path, state)
    payload: dict[str, Any] = {
        "generated_at": utc_now(),
        "active_round_detected": state.active_round_detected,
        "active_round_id": round_id,
        "new_round_detected": bool(state.active_round_detected and not duplicate_round),
        "duplicate_round_ignored": duplicate_round,
        "paused_for_manual_gate": bool(detection.get("paused_for_manual_gate", False)),
        "manual_gate_reason": detection.get("manual_gate_reason", ""),
        "submission_attempted": False,
        "blocker": blocker or "",
        "rounds_processed": state.rounds_processed,
    }
    write_json(project_root / config.paths.round_watcher_status_json_path, payload)
    write_markdown(project_root / config.paths.round_watcher_status_md_path, "Beat Battle Round Watcher Status", payload)
    return payload


def update_agent_status(project_root: Path, config: BeatBattleAgentConfig, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    state = load_or_default_state(project_root / config.paths.local_state_path)
    payload: dict[str, Any] = {
        "updated_at": state.updated_at,
        "active_round_detected": state.active_round_detected,
        "active_round_id": state.active_round_id or "",
        "rounds_processed": state.rounds_processed,
        "sounds_acquired": state.sounds_acquired,
        "synplant_variations_generated": state.synplant_variations_generated,
        "useful_variations_saved": state.useful_variations_saved,
        "drafts_generated": state.drafts_generated,
        "submission_attempted": state.submission_attempted,
        "submitted": state.submitted,
        "result_logged": state.result_logged,
        "battle_outcome_ranker_trained": state.battle_outcome_ranker_trained,
        "training_results_count": state.training_results_count,
        "blockers": ",".join(state.blockers),
    }
    if extra:
        payload.update(extra)
    write_json(project_root / config.paths.status_json_path, payload)
    write_markdown(project_root / config.paths.status_md_path, "Beat Battle Agent Status", payload)
    return payload
