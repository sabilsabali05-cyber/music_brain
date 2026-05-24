from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .site_adapter import extract_round_rows, validate_selectors
from .site_config_schema import BeatBattleRankedSiteConfig


@dataclass(frozen=True)
class RoundDetectionResult:
    active_round_detected: bool
    round_id: str
    blocker: str | None
    diagnostics: dict[str, Any]
    sound_urls: list[str]


def detect_active_round(config: BeatBattleRankedSiteConfig, snapshot_payload: dict[str, Any]) -> RoundDetectionResult:
    selector_diag = validate_selectors(config)
    if not selector_diag.ok:
        return RoundDetectionResult(
            active_round_detected=False,
            round_id="",
            blocker="missing_selectors",
            diagnostics={"missing_selectors": selector_diag.missing},
            sound_urls=[],
        )
    rows = extract_round_rows(snapshot_payload)
    for row in rows:
        status = str(row.get("status", "")).strip().lower()
        if status == "active":
            round_id = str(row.get("round_id", "")).strip()
            sound_urls = [str(x) for x in row.get("sound_urls", []) if str(x).strip()]
            return RoundDetectionResult(
                active_round_detected=bool(round_id),
                round_id=round_id,
                blocker=None if round_id else "active_round_missing_id",
                diagnostics={"round_cards_seen": len(rows)},
                sound_urls=sound_urls,
            )
    return RoundDetectionResult(
        active_round_detected=False,
        round_id="",
        blocker="active_round_not_found",
        diagnostics={"round_cards_seen": len(rows)},
        sound_urls=[],
    )


def read_snapshot(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}
