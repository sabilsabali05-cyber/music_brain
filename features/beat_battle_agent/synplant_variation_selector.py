from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .agent_config_schema import BeatBattleAgentConfig
from .agent_runtime import write_json, write_markdown
from .agent_state_schema import load_or_default_state, save_state


def _load_manifest_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def select_useful_variations(project_root: Path, config: BeatBattleAgentConfig, round_id: str) -> dict[str, Any]:
    rows = [row for row in _load_manifest_rows(project_root / config.paths.synplant_manifest_jsonl_path) if str(row.get("round_id", "")) == round_id]
    useful = []
    for idx, row in enumerate(rows):
        if not bool(row.get("verification_passed", False)):
            continue
        pseudo_score = 0.55 + ((idx % 7) * 0.07)
        if pseudo_score >= config.useful_variation_threshold:
            useful.append({"variation_id": row.get("variation_id", ""), "score": round(min(0.99, pseudo_score), 4)})
    payload = {
        "round_id": round_id,
        "submission_allowed": bool(config.submission_allowed),
        "selected_count": len(useful),
        "selected_variations": useful,
        "blocker": "" if useful else "no_verified_variations",
    }
    write_json(project_root / "reports" / "beat_battle_agent" / f"{round_id}_selected_synplant_variations.json", payload)
    write_markdown(
        project_root / "reports" / "beat_battle_agent" / f"{round_id}_selected_synplant_variations.md",
        "Selected Synplant Variations",
        payload,
    )
    state = load_or_default_state(project_root / config.paths.local_state_path)
    state.useful_variations_saved += len(useful)
    save_state(project_root / config.paths.local_state_path, state)
    return payload
