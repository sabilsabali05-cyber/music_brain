from __future__ import annotations

from pathlib import Path

from features.beat_battle_site_automation.browser_session import setup_browser_session, validate_automation_safety
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


def test_validate_automation_safety_accepts_default_safe_config() -> None:
    ok, blocker = validate_automation_safety(_config())
    assert ok is True
    assert blocker is None


def test_setup_browser_session_requires_manual_action_when_playwright_missing_or_login_required(tmp_path: Path) -> None:
    result = setup_browser_session(_config(), tmp_path)
    assert result.manual_action_required is True
    assert result.blocker in {
        "playwright_not_installed",
        "manual_login_capture_required",
        "manual_navigation_required",
        "playwright_runtime_unavailable",
    }
    assert Path(result.storage_state_path).name.endswith(".json")
