from __future__ import annotations

from pathlib import Path

from features.beat_battle_site_automation.site_config_schema import BeatBattleRankedSiteConfig
from features.beat_battle_site_automation.submission_uploader import submit_entry


def _config() -> BeatBattleRankedSiteConfig:
    return BeatBattleRankedSiteConfig.model_validate(
        {
            "site_name": "Beat Battle Ranked",
            "base_url": "https://example.invalid",
            "ranked_path": "/ranked",
            "user_handle": "tester",
        }
    )


def test_submit_stops_before_submit_when_manual_confirmation_required(tmp_path: Path) -> None:
    render_path = tmp_path / "submission.wav"
    render_path.write_bytes(b"RIFF")
    result = submit_entry(config=_config(), render_path=render_path, manual_submit_confirmed=False)
    assert result.submitted is False
    assert result.upload_success is False
    assert result.stopped_pre_submit is True
    assert result.blocker == "manual_submit_confirmation_required"
