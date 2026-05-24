from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .site_config_schema import BeatBattleRankedSiteConfig


@dataclass(frozen=True)
class BrowserSessionSetupResult:
    ok: bool
    manual_action_required: bool
    blocker: str | None
    storage_state_path: str
    notes: list[str]


def validate_automation_safety(config: BeatBattleRankedSiteConfig) -> tuple[bool, str | None]:
    if config.safety.allow_bot_evasion:
        return False, "bot_evasion_disallowed"
    if config.safety.allow_multi_account:
        return False, "multi_account_disallowed"
    if config.safety.allow_captcha_bypass:
        return False, "captcha_bypass_disallowed"
    if config.safety.allow_login_bypass or config.safety.allow_mfa_bypass:
        return False, "auth_bypass_disallowed"
    return True, None


def setup_browser_session(config: BeatBattleRankedSiteConfig, project_root: Path) -> BrowserSessionSetupResult:
    safe, blocker = validate_automation_safety(config)
    state_path = (project_root / config.session.storage_state_path).resolve()
    if not safe:
        return BrowserSessionSetupResult(
            ok=False,
            manual_action_required=True,
            blocker=blocker,
            storage_state_path=state_path.as_posix(),
            notes=["Safety policy blocked session setup."],
        )

    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps(
                {
                    "capture_status": "manual_capture_required",
                    "site": config.site_name,
                    "reason": "playwright_not_installed",
                },
                indent=2,
                ensure_ascii=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return BrowserSessionSetupResult(
            ok=False,
            manual_action_required=True,
            blocker="playwright_not_installed",
            storage_state_path=state_path.as_posix(),
            notes=["Install Playwright, then perform manual login/captcha/MFA in browser."],
        )

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=config.session.headless)
            context = browser.new_context()
            page = context.new_page()
            try:
                page.goto(f"{config.base_url.rstrip('/')}/{config.ranked_path.lstrip('/')}", wait_until="domcontentloaded")
                context.storage_state(path=state_path.as_posix())
            except Exception:
                browser.close()
                state_path.parent.mkdir(parents=True, exist_ok=True)
                state_path.write_text(
                    json.dumps(
                        {
                            "capture_status": "manual_capture_required",
                            "site": config.site_name,
                            "reason": "manual_navigation_required",
                        },
                        indent=2,
                        ensure_ascii=True,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                return BrowserSessionSetupResult(
                    ok=False,
                    manual_action_required=True,
                    blocker="manual_navigation_required",
                    storage_state_path=state_path.as_posix(),
                    notes=["Open the site manually and complete login/captcha/MFA before continuing."],
                )
            browser.close()
    except Exception:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps(
                {
                    "capture_status": "manual_capture_required",
                    "site": config.site_name,
                    "reason": "playwright_runtime_unavailable",
                },
                indent=2,
                ensure_ascii=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return BrowserSessionSetupResult(
            ok=False,
            manual_action_required=True,
            blocker="playwright_runtime_unavailable",
            storage_state_path=state_path.as_posix(),
            notes=["Playwright runtime is unavailable in this environment; complete session capture manually."],
        )

    return BrowserSessionSetupResult(
        ok=True,
        manual_action_required=True,
        blocker="manual_login_capture_required",
        storage_state_path=state_path.as_posix(),
        notes=[
            "Storage state initialized.",
            "Run the setup script interactively and complete login/captcha/MFA manually.",
        ],
    )


def as_dict(result: BrowserSessionSetupResult) -> dict[str, Any]:
    return {
        "ok": result.ok,
        "manual_action_required": result.manual_action_required,
        "blocker": result.blocker,
        "storage_state_path": result.storage_state_path,
        "notes": result.notes,
    }
