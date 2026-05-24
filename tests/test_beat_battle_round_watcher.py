from __future__ import annotations

import json
from pathlib import Path

from features.beat_battle_agent.agent_config_schema import load_agent_config
from features.beat_battle_agent.round_watcher import watch_round_once


def test_round_watcher_pauses_on_login_gate(tmp_path: Path) -> None:
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "beat_battle_agent.local.json").write_text(
        json.dumps({"site_config_path": "config/beat_battle_ranked_site.local.json"}),
        encoding="utf-8",
    )
    (tmp_path / "config" / "beat_battle_ranked_site.local.json").write_text(
        json.dumps(
            {
                "site_name": "Beat Battle Ranked",
                "base_url": "https://example.invalid",
                "ranked_path": "/ranked",
                "user_handle": "tester",
                "session": {"manual_round_snapshot_path": "artifacts/beat_battle_site/manual_round_snapshot.json"},
            }
        ),
        encoding="utf-8",
    )
    snapshot_path = tmp_path / "artifacts" / "beat_battle_site" / "manual_round_snapshot.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps({"login_required": True}), encoding="utf-8")
    config = load_agent_config(tmp_path / "config" / "beat_battle_agent.local.json")
    payload = watch_round_once(tmp_path, config)
    assert payload["paused_for_manual_gate"] is True
    assert payload["manual_gate_reason"] == "login_required"
    assert payload["submission_attempted"] is False
