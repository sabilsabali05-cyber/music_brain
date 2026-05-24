from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ALLOWED_MODE = "manual_or_authorized_only"
AUTHORIZATION_ARTIFACT_PATH = Path("config/beat_battle_automation_authorization.txt")


def has_live_automation_authorization(project_root: Path) -> bool:
    artifact = project_root / AUTHORIZATION_ARTIFACT_PATH
    if not artifact.exists():
        return False
    return bool(artifact.read_text(encoding="utf-8").strip())


def build_compliance_snapshot(project_root: Path, mode: str = ALLOWED_MODE) -> dict[str, Any]:
    authorized = has_live_automation_authorization(project_root)
    return {
        "mode": mode,
        "live_site_automation_enabled": False,
        "auto_submit_enabled": False,
        "manual_submission_required": True,
        "synplant_variations_submission_allowed": False,
        "synplant_variations_study_allowed": True,
        "raw_round_sounds_committed": False,
        "authorization_artifact_present": authorized,
        "live_automation_blocked_reason": "manual_or_authorized_only",
    }


def assert_live_automation_allowed(project_root: Path, mode: str = ALLOWED_MODE) -> tuple[bool, str]:
    _ = build_compliance_snapshot(project_root, mode=mode)
    return False, "live_automation_disabled_in_study_mode"


def write_compliance_reports(project_root: Path, mode: str = ALLOWED_MODE) -> dict[str, Any]:
    snapshot = build_compliance_snapshot(project_root, mode=mode)
    reports_root = project_root / "reports" / "beat_battle_agent"
    reports_root.mkdir(parents=True, exist_ok=True)
    report_json = reports_root / "compliance_status.json"
    report_md = reports_root / "compliance_status.md"
    report_json.write_text(json.dumps(snapshot, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    report_md.write_text(
        "\n".join(
            [
                "# Beat Battle Compliance Status",
                "",
                f"- mode: `{snapshot['mode']}`",
                "- live_site_automation_enabled: `false`" if not snapshot["live_site_automation_enabled"] else "- live_site_automation_enabled: `true`",
                "- auto_submit_enabled: `false`",
                "- manual_submission_required: `true`",
                "- synplant_variations_submission_allowed: `false`",
                "- synplant_variations_study_allowed: `true`",
                "- raw_round_sounds_committed: `false`",
                f"- authorization_artifact_present: `{str(snapshot['authorization_artifact_present']).lower()}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return snapshot
