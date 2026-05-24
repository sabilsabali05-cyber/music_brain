from __future__ import annotations

import json

from features.beat_battle_agent.agent_config_schema import load_agent_config
from features.beat_battle_agent.winner_pattern_study import study_winner_patterns


def test_winner_pattern_study_blocks_without_results(tmp_path) -> None:
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    config_path = tmp_path / "config" / "beat_battle_agent.local.json"
    config_path.write_text(json.dumps({}), encoding="utf-8")
    config = load_agent_config(config_path)
    payload = study_winner_patterns(tmp_path, config)
    assert payload["composition"]["blocker"] == "no_results_logged"
    assert payload["sound_design"]["blocker"] == "no_results_logged"
