from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class BeatBattleAgentState(BaseModel):
    agent_version: str = "v1"
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    rounds_seen: list[str] = Field(default_factory=list)
    rounds_processed: int = 0
    active_round_detected: bool = False
    active_round_id: str = ""
    sounds_acquired: int = 0
    synplant_variations_generated: int = 0
    useful_variations_saved: int = 0
    drafts_generated: int = 0
    submission_attempted: bool = False
    submitted: bool = False
    result_logged: bool = False
    battle_outcome_ranker_trained: bool = False
    training_results_count: int = 0
    last_submission_round_id: str = ""
    blockers: list[str] = Field(default_factory=list)


def load_or_default_state(path: Path) -> BeatBattleAgentState:
    if not path.exists():
        return BeatBattleAgentState()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return BeatBattleAgentState(blockers=["invalid_state_file"])
    if not isinstance(payload, dict):
        return BeatBattleAgentState(blockers=["invalid_state_payload"])
    return BeatBattleAgentState.model_validate(payload)


def save_state(path: Path, state: BeatBattleAgentState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state.updated_at = datetime.now(UTC).isoformat()
    path.write_text(json.dumps(state.model_dump(mode="json"), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def write_agent_status_reports(status_json_path: Path, status_md_path: Path, payload: dict[str, Any]) -> None:
    status_json_path.parent.mkdir(parents=True, exist_ok=True)
    status_json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = ["# Beat Battle Agent Status", ""]
    for key, value in payload.items():
        lines.append(f"- {key}: `{value}`")
    lines.append("")
    status_md_path.write_text("\n".join(lines), encoding="utf-8")
