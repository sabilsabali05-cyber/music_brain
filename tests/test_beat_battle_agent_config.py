from __future__ import annotations

from pathlib import Path

from features.beat_battle_agent.agent_config_schema import BeatBattleAgentConfig, load_optional_local_agent_config


def test_agent_config_rejects_unsafe_flags() -> None:
    payload = {
        "site_config_path": "config/beat_battle_ranked_site.local.json",
        "safety": {"allow_captcha_bypass": True},
    }
    try:
        BeatBattleAgentConfig.model_validate(payload)
    except Exception:
        return
    raise AssertionError("Unsafe bypass flags must be rejected.")


def test_agent_config_missing_local_file_is_safe_blocker(tmp_path: Path) -> None:
    config, blocker = load_optional_local_agent_config(tmp_path)
    assert config is None
    assert blocker == "missing_local_agent_config"
