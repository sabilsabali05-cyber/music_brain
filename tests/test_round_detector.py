from __future__ import annotations

from features.beat_battle_site_automation.round_detector import detect_active_round
from features.beat_battle_site_automation.site_config_schema import BeatBattleRankedSiteConfig


def _config() -> BeatBattleRankedSiteConfig:
    return BeatBattleRankedSiteConfig.model_validate(
        {
            "site_name": "Beat Battle Ranked",
            "base_url": "https://example.invalid",
            "ranked_path": "/ranked",
            "user_handle": "tester",
        }
    )


def test_detect_round_from_snapshot_payload() -> None:
    payload = {
        "round_cards": [
            {"round_id": "R1", "status": "closed", "sound_urls": ["https://x.invalid/a.wav"]},
            {"round_id": "R2", "status": "active", "sound_urls": ["https://x.invalid/b.wav", "https://x.invalid/c.wav"]},
        ]
    }
    result = detect_active_round(_config(), payload)
    assert result.active_round_detected is True
    assert result.round_id == "R2"
    assert len(result.sound_urls) == 2


def test_detect_round_missing_returns_blocker() -> None:
    result = detect_active_round(_config(), {"round_cards": []})
    assert result.active_round_detected is False
    assert result.blocker == "active_round_not_found"
