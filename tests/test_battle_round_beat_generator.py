from __future__ import annotations

import json

from features.beat_battle_agent.agent_config_schema import load_agent_config
from features.beat_battle_agent.round_beat_generator import generate_round_beats


def test_round_beat_generator_builds_minimum_drafts(tmp_path) -> None:
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    config_path = tmp_path / "config" / "beat_battle_agent.local.json"
    config_path.write_text(json.dumps({}), encoding="utf-8")
    manual_manifest = tmp_path / "datasets" / "beat_battle_agent" / "manual_rounds" / "round_manifest.json"
    manual_manifest.parent.mkdir(parents=True, exist_ok=True)
    manual_manifest.write_text(json.dumps({"round_id": "R1", "sounds": [{"sound_id": "s1"}]}), encoding="utf-8")
    (tmp_path / "datasets" / "beat_battle_agent" / "manual_rounds" / "latest_round_manifest.txt").write_text(
        manual_manifest.as_posix(),
        encoding="utf-8",
    )
    selected_path = tmp_path / "reports" / "beat_battle_agent" / "R1_selected_synplant_variations.json"
    selected_path.parent.mkdir(parents=True, exist_ok=True)
    selected_path.write_text(json.dumps({"selected_count": 0}), encoding="utf-8")
    config = load_agent_config(config_path)
    payload = generate_round_beats(tmp_path, config, "R1")
    assert payload["drafts_generated"] >= 8
    assert payload["legal_sound_usage_only"] is True
