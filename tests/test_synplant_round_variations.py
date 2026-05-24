from __future__ import annotations

import json
from pathlib import Path

from features.beat_battle_agent.agent_config_schema import load_agent_config
from features.beat_battle_agent.synplant_round_variations import generate_synplant_variations


def test_synplant_variations_require_round_manifest(tmp_path: Path) -> None:
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    config_path = tmp_path / "config" / "beat_battle_agent.local.json"
    config_path.write_text(json.dumps({}), encoding="utf-8")
    config = load_agent_config(config_path)
    result = generate_synplant_variations(tmp_path, config)
    assert result["ok"] is False
    assert result["blocker"] == "missing_round_manifest"


def test_synplant_variations_generate_verified_rows(tmp_path: Path) -> None:
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    config_path = tmp_path / "config" / "beat_battle_agent.local.json"
    config_path.write_text(json.dumps({}), encoding="utf-8")
    manifest_path = tmp_path / "datasets" / "beat_battle_site" / "rounds" / "R1" / "round_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"round_id": "R1", "sounds": [{"sound_id": "s1"}]}), encoding="utf-8")
    config = load_agent_config(config_path)
    result = generate_synplant_variations(tmp_path, config)
    assert result["ok"] is True
    assert result["strict_no_fake_usage"] is True
