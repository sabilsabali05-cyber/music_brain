from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .agent_config_schema import BeatBattleAgentConfig
from .agent_runtime import write_json, write_markdown
from .result_memory_schema import BeatBattleResultMemory


def _load_rows(path: Path) -> list[dict[str, Any]]:
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


def analyze_results(project_root: Path, config: BeatBattleAgentConfig) -> dict[str, Any]:
    result_path = project_root / config.paths.results_dataset_jsonl_path
    rows = [BeatBattleResultMemory.model_validate(row) for row in _load_rows(result_path)]
    wins = [row for row in rows if row.placement is not None and row.placement <= 3]
    submitted = [row for row in rows if row.submitted]
    payload = {
        "results_count": len(rows),
        "submitted_count": len(submitted),
        "top3_count": len(wins),
        "win_rate": round((len(wins) / len(submitted)), 4) if submitted else 0.0,
        "authorized_rows_count": len([row for row in rows if row.source_authorized_for_learning]),
        "blocker": "" if rows else "no_results_logged",
    }
    write_json(project_root / "reports" / "beat_battle_agent" / "battle_results_analysis.json", payload)
    write_markdown(project_root / "reports" / "beat_battle_agent" / "battle_results_analysis.md", "Battle Results Analysis", payload)
    (project_root / "datasets" / "beat_battle_agent").mkdir(parents=True, exist_ok=True)
    (project_root / "datasets" / "beat_battle_agent" / "battle_results_summary.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return payload
