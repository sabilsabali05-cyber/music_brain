from __future__ import annotations

import json
from pathlib import Path

from features.beat_battle_site_automation.site_config_schema import BeatBattleRankedSiteConfig, load_optional_local_site_config


def test_schema_rejects_unsafe_bypass_flags() -> None:
    payload = {
        "site_name": "Beat Battle Ranked",
        "base_url": "https://example.invalid",
        "ranked_path": "/ranked",
        "user_handle": "tester",
        "safety": {"allow_captcha_bypass": True},
    }
    try:
        BeatBattleRankedSiteConfig.model_validate(payload)
    except Exception:
        return
    raise AssertionError("Schema should reject unsafe bypass flags.")


def test_load_optional_local_site_config_missing_file(tmp_path: Path) -> None:
    config, blocker = load_optional_local_site_config(tmp_path)
    assert config is None
    assert blocker == "missing_local_site_config"


def test_load_optional_local_site_config_success(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    local_path = config_dir / "beat_battle_ranked_site.local.json"
    local_path.write_text(
        json.dumps(
            {
                "site_name": "Beat Battle Ranked",
                "base_url": "https://example.invalid",
                "ranked_path": "/ranked",
                "user_handle": "tester",
            }
        ),
        encoding="utf-8",
    )
    config, blocker = load_optional_local_site_config(tmp_path)
    assert blocker is None
    assert config is not None
    assert config.user_handle == "tester"
