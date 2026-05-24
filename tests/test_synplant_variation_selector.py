from __future__ import annotations

import json

from features.beat_battle_agent.agent_config_schema import load_agent_config
from features.beat_battle_agent.synplant_variation_selector import select_useful_variations


def test_selector_respects_submission_allowed_flag(tmp_path) -> None:
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    config_path = tmp_path / "config" / "beat_battle_agent.local.json"
    config_path.write_text(json.dumps({"submission_allowed": False}), encoding="utf-8")
    manifest = tmp_path / "datasets" / "beat_battle_agent" / "synplant_variation_manifest.jsonl"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps({"round_id": "R1", "variation_id": "v1", "verification_passed": True}) + "\n",
        encoding="utf-8",
    )
    config = load_agent_config(config_path)
    payload = select_useful_variations(tmp_path, config, "R1")
    assert payload["submission_allowed"] is False
