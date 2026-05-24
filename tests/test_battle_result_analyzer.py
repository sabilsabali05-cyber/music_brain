from __future__ import annotations

import json

from features.beat_battle_agent.agent_config_schema import load_agent_config
from features.beat_battle_agent.result_analyzer import analyze_results


def test_result_analyzer_reports_safe_blocker_when_empty(tmp_path) -> None:
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    config_path = tmp_path / "config" / "beat_battle_agent.local.json"
    config_path.write_text(json.dumps({}), encoding="utf-8")
    config = load_agent_config(config_path)
    payload = analyze_results(tmp_path, config)
    assert payload["results_count"] == 0
    assert payload["blocker"] == "no_results_logged"
