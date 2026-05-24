from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from features.beat_battle_site_automation.round_detector import detect_active_round, read_snapshot
from features.beat_battle_site_automation.site_config_schema import load_optional_local_site_config

from .agent_config_schema import BeatBattleAgentConfig


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def write_markdown(path: Path, title: str, payload: dict[str, Any]) -> None:
    lines = [f"# {title}", ""]
    for key, value in payload.items():
        lines.append(f"- {key}: `{value}`")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def detect_round_status(project_root: Path, config: BeatBattleAgentConfig) -> dict[str, Any]:
    site_config, site_blocker = load_optional_local_site_config(project_root)
    if site_config is None:
        return {
            "active_round_detected": False,
            "active_round_id": "",
            "blocker": site_blocker or "missing_local_site_config",
            "paused_for_manual_gate": True,
            "manual_gate_reason": site_blocker or "missing_local_site_config",
        }
    snapshot = read_snapshot((project_root / site_config.session.manual_round_snapshot_path).resolve())
    login_required = bool(snapshot.get("login_required", False))
    captcha_required = bool(snapshot.get("captcha_required", False))
    mfa_required = bool(snapshot.get("mfa_required", False))
    manual_required = bool(snapshot.get("manual_challenge_required", False))
    if login_required and config.safety.stop_on_login_required:
        return {
            "active_round_detected": False,
            "active_round_id": "",
            "blocker": "login_required",
            "paused_for_manual_gate": True,
            "manual_gate_reason": "login_required",
        }
    if (captcha_required or mfa_required) and config.safety.stop_on_captcha_required:
        return {
            "active_round_detected": False,
            "active_round_id": "",
            "blocker": "captcha_or_mfa_required",
            "paused_for_manual_gate": True,
            "manual_gate_reason": "captcha_or_mfa_required",
        }
    if manual_required and config.safety.stop_on_manual_challenge_required:
        return {
            "active_round_detected": False,
            "active_round_id": "",
            "blocker": "manual_challenge_required",
            "paused_for_manual_gate": True,
            "manual_gate_reason": "manual_challenge_required",
        }
    result = detect_active_round(site_config, snapshot)
    return {
        "active_round_detected": result.active_round_detected,
        "active_round_id": result.round_id,
        "sound_urls_count": len(result.sound_urls),
        "blocker": result.blocker or "",
        "paused_for_manual_gate": False,
        "manual_gate_reason": "",
    }
