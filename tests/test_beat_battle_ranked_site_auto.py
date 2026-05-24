from __future__ import annotations

from scripts.beat_battle_ranked_site_auto import build_status


def test_auto_status_fails_safely_when_local_config_missing() -> None:
    status = build_status()
    assert "site_configured" in status
    if status["site_configured"] is False:
        assert status["blocker"] == "missing_local_site_config"
        assert status["active_round_detected"] is False
        assert status["sounds_acquired"] is False
