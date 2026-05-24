from __future__ import annotations

from features.beat_battle_agent.agent_config_schema import BeatBattleAgentConfig


def test_once_flow_defaults_to_no_auto_submit() -> None:
    config = BeatBattleAgentConfig.model_validate({})
    assert config.safety.auto_submit is False
    assert config.safety.require_manual_submit_confirmation is True
    assert config.submission_allowed is False
