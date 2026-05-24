from __future__ import annotations

import json
from pathlib import Path

from features.beat_battle_site_automation.site_config_schema import BeatBattleRankedSiteConfig
from features.beat_battle_site_automation.sound_acquisition import acquire_round_sounds


def _config() -> BeatBattleRankedSiteConfig:
    return BeatBattleRankedSiteConfig.model_validate(
        {
            "site_name": "Beat Battle Ranked",
            "base_url": "https://example.invalid",
            "ranked_path": "/ranked",
            "user_handle": "tester",
            "acquisition": {"strategies": ["snapshot_sound_links"]},
        }
    )


def test_acquire_round_sounds_writes_committed_manifest(tmp_path: Path) -> None:
    result = acquire_round_sounds(
        config=_config(),
        project_root=tmp_path,
        round_id="round_001",
        round_sound_urls=["https://x.invalid/kick.wav", "https://x.invalid/snare.wav"],
    )
    assert result.sounds_acquired is True
    assert result.acquired_count == 2
    manifest_path = Path(result.manifest_path)
    assert manifest_path.exists()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["round_id"] == "round_001"
    assert payload["policy"]["raw_audio_stored_local_only"] is True
