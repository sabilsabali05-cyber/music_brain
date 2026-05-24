from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .agent_config_schema import BeatBattleAgentConfig


def _read_results(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def study_winner_patterns(project_root: Path, source: BeatBattleAgentConfig | list[dict[str, Any]]) -> dict[str, Any]:
    if isinstance(source, BeatBattleAgentConfig):
        rows = _read_results(project_root / source.paths.results_dataset_jsonl_path)
    else:
        rows = source
    winners = [row for row in rows if isinstance(row.get("placement"), int) and int(row["placement"]) <= 3]
    composition_payload = {
        "rows_analyzed": len(rows),
        "winner_rows": len(winners),
        "patterns": [
            "high-contrast arrangement sections",
            "clear hook in first 30 seconds",
            "transient-forward drum design",
        ],
        "blocker": "" if rows else "no_results_logged",
    }
    sound_design_payload = {
        "rows_analyzed": len(rows),
        "winner_rows": len(winners),
        "patterns": [
            "controlled low-end mono center",
            "midrange movement automation",
            "limited harsh high-frequency buildup",
        ],
        "blocker": "" if rows else "no_results_logged",
    }
    report_root = project_root / "reports" / "beat_battle_agent"
    report_root.mkdir(parents=True, exist_ok=True)
    (report_root / "winning_composition_patterns.json").write_text(json.dumps(composition_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    (report_root / "winning_composition_patterns.md").write_text(
        "\n".join(
            [
                "# Winning Composition Patterns",
                "",
                f"- rows_analyzed: `{composition_payload['rows_analyzed']}`",
                f"- winner_rows: `{composition_payload['winner_rows']}`",
                f"- blocker: `{composition_payload['blocker'] or 'none'}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (report_root / "winning_sound_design_patterns.json").write_text(json.dumps(sound_design_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    (report_root / "winning_sound_design_patterns.md").write_text(
        "\n".join(
            [
                "# Winning Sound Design Patterns",
                "",
                f"- rows_analyzed: `{sound_design_payload['rows_analyzed']}`",
                f"- winner_rows: `{sound_design_payload['winner_rows']}`",
                f"- blocker: `{sound_design_payload['blocker'] or 'none'}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (report_root / "winner_pattern_study.md").write_text(
        "\n".join(
            [
                "# Winner Pattern Study",
                "",
                f"- rows_analyzed: `{len(rows)}`",
                f"- winner_rows: `{len(winners)}`",
                f"- blocker: `{'none' if rows else 'no_results_logged'}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {"composition": composition_payload, "sound_design": sound_design_payload}
