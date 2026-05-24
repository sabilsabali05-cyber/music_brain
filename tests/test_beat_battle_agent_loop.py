from __future__ import annotations

from features.beat_battle_agent.agent_config_schema import BeatBattleAgentConfig


def test_loop_config_has_safe_iteration_limits() -> None:
    config = BeatBattleAgentConfig.model_validate({})
    assert config.max_rounds_per_loop >= 1
    assert config.poll_interval_seconds >= 5
