from __future__ import annotations

import json
from pathlib import Path

from features.beat_battle_site_automation.result_scraper import ingest_result
from features.beat_battle_site_automation.site_config_schema import BeatBattleRankedSiteConfig


def _config() -> BeatBattleRankedSiteConfig:
    return BeatBattleRankedSiteConfig.model_validate(
        {
            "site_name": "Beat Battle Ranked",
            "base_url": "https://example.invalid",
            "ranked_path": "/ranked",
            "user_handle": "tester",
            "session": {"manual_result_snapshot_path": "artifacts/beat_battle_site/manual_result_snapshot.json"},
        }
    )


def test_ingest_result_collects_only_allowed_fields(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "artifacts" / "beat_battle_site" / "manual_result_snapshot.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(
        json.dumps(
            {
                "round_id": "R-100",
                "placement": 7,
                "score": 91.5,
                "votes": 81,
                "result_url": "https://example.invalid/result",
                "result_available": True,
                "private_profile_email": "should_not_be_collected@example.com",
            }
        ),
        encoding="utf-8",
    )
    result = ingest_result(_config(), tmp_path)
    assert result.result_available is True
    assert result.feedback_ingested is True
    assert "private_profile_email" not in result.result_record
