from __future__ import annotations

from pathlib import Path
from typing import Any

from .agent_config_schema import BeatBattleAgentConfig
from .agent_runtime import read_json, write_json, write_markdown


def build_dashboard(project_root: Path, config: BeatBattleAgentConfig, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    status = read_json(project_root / config.paths.status_json_path)
    once = read_json(project_root / "reports" / "beat_battle_agent" / "beat_battle_agent_once.json")
    training = read_json(project_root / "reports" / "beat_battle_agent" / "battle_outcome_ranker_training.json")
    payload: dict[str, Any] = {
        "site_configured": bool(status),
        "active_round_detected": bool(status.get("active_round_detected", False)),
        "rounds_processed": int(status.get("rounds_processed", 0)),
        "sounds_acquired": int(status.get("sounds_acquired", 0)),
        "synplant_variations_generated": int(status.get("synplant_variations_generated", 0)),
        "useful_variations_saved": int(status.get("useful_variations_saved", 0)),
        "drafts_generated": int(status.get("drafts_generated", 0)),
        "submission_attempted": bool(once.get("submission_attempted", False)),
        "submitted": bool(once.get("submitted", False)),
        "result_logged": bool(once.get("result_logged", False)),
        "battle_outcome_ranker_trained": bool(training.get("battle_outcome_ranker_trained", False)),
        "training_results_count": int(training.get("results_count", 0)),
        "blocker": str(status.get("blockers", "")).strip(),
        "safety_constraints_enforced": True,
    }
    if extra:
        payload.update(extra)
    write_json(project_root / config.paths.dashboard_json_path, payload)
    write_markdown(project_root / config.paths.dashboard_md_path, "Beat Battle Agent Dashboard", payload)
    return payload
