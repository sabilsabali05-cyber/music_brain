from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .site_config_schema import BeatBattleRankedSiteConfig


REQUIRED_SELECTOR_FIELDS = [
    "login_gate",
    "captcha_gate",
    "mfa_gate",
    "manual_confirmation_gate",
    "active_round_card",
    "active_round_id",
    "active_round_status",
    "active_round_sound_links",
    "upload_input",
    "submit_button",
    "result_row",
]


@dataclass(frozen=True)
class SelectorDiagnostics:
    ok: bool
    missing: list[str]
    configured: dict[str, str]


def validate_selectors(config: BeatBattleRankedSiteConfig) -> SelectorDiagnostics:
    configured = config.selectors.model_dump()
    missing: list[str] = []
    for field_name in REQUIRED_SELECTOR_FIELDS:
        value = str(configured.get(field_name, "")).strip()
        if not value:
            missing.append(field_name)
    return SelectorDiagnostics(ok=not missing, missing=missing, configured=configured)


def extract_round_rows(snapshot_payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = snapshot_payload.get("round_cards")
    if isinstance(rows, list):
        return [item for item in rows if isinstance(item, dict)]
    return []
