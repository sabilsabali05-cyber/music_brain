from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.check_privacy_leaks import scan_privacy_leaks  # noqa: E402
from features.beat_battle_site_automation.site_config_schema import load_optional_local_site_config  # noqa: E402


def _run(script_name: str) -> int:
    command = [sys.executable, str(ROOT_DIR / "scripts" / script_name)]
    result = subprocess.run(command, cwd=ROOT_DIR, check=False, capture_output=True, text=True)
    return result.returncode


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _git_read(command: list[str]) -> str:
    result = subprocess.run(command, cwd=ROOT_DIR, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def build_status() -> dict[str, Any]:
    config, blocker = load_optional_local_site_config(ROOT_DIR)
    branch = _git_read(["git", "branch", "--show-current"])
    commit_hash = _git_read(["git", "rev-parse", "HEAD"])
    git_status = _git_read(["git", "status", "--short"])
    privacy_payload = scan_privacy_leaks(project_root=ROOT_DIR, strict_mode=False)

    status: dict[str, Any] = {
        "branch": branch,
        "commit hash": commit_hash,
        "site_configured": config is not None,
        "active_round_detected": False,
        "sounds_acquired": False,
        "drafts_generated": False,
        "rendered_submission_available": False,
        "upload_success": False,
        "submitted": False,
        "result_available": False,
        "feedback_ingested": False,
        "blocker": blocker,
        "privacy result": privacy_payload.get("status", "unknown"),
        "git status": git_status or "clean",
    }
    if config is None:
        status["blocker"] = "missing_local_site_config"
        return status

    _run("detect_beat_battle_round.py")
    detect_report = _read_json(ROOT_DIR / "reports" / "beat_battle_site_automation" / "round_detection_report.json")
    status["active_round_detected"] = bool(detect_report.get("active_round_detected", False))
    if not status["active_round_detected"]:
        status["blocker"] = detect_report.get("blocker") or "active_round_not_found"
        return status

    _run("acquire_beat_battle_round_sounds.py")
    acquire_report = _read_json(ROOT_DIR / "reports" / "beat_battle_site_automation" / "sound_acquisition_report.json")
    status["sounds_acquired"] = bool(acquire_report.get("sounds_acquired", False))
    if not status["sounds_acquired"]:
        status["blocker"] = acquire_report.get("blocker") or "no_round_sounds_acquired"
        return status

    _run("generate_beat_battle_drafts.py")
    ranked_path = ROOT_DIR / "outputs" / "beat_battle_site"
    ranked_candidates = sorted(ranked_path.glob("*/ranked_drafts.json"))
    status["drafts_generated"] = bool(ranked_candidates)
    if not status["drafts_generated"]:
        status["blocker"] = "draft_generation_failed"
        return status

    _run("render_beat_battle_submission.py")
    render_report = _read_json(ROOT_DIR / "reports" / "beat_battle_site_automation" / "submission_render_report.json")
    status["rendered_submission_available"] = bool(render_report.get("rendered_submission_available", False))

    _run("submit_beat_battle_entry.py")
    submission_report = _read_json(ROOT_DIR / "reports" / "beat_battle_site_automation" / "submission_report.json")
    status["upload_success"] = bool(submission_report.get("upload_success", False))
    status["submitted"] = bool(submission_report.get("submitted", False))

    _run("check_beat_battle_result.py")
    result_report = _read_json(ROOT_DIR / "reports" / "beat_battle_site_automation" / "result_report.json")
    status["result_available"] = bool(result_report.get("result_available", False))
    status["feedback_ingested"] = bool(result_report.get("feedback_ingested", False))
    if not status["result_available"] and not status.get("blocker"):
        status["blocker"] = result_report.get("blocker") or submission_report.get("blocker")
    return status


def main() -> int:
    status = build_status()
    status["generated_at"] = datetime.now(UTC).isoformat()
    report_root = ROOT_DIR / "reports" / "beat_battle_site_automation"
    report_json = report_root / "site_auto_status.json"
    report_md = report_root / "site_auto_status.md"
    report_root.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(status, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = ["# Beat Battle Ranked Site Auto Status", ""]
    for key in [
        "branch",
        "commit hash",
        "site_configured",
        "active_round_detected",
        "sounds_acquired",
        "drafts_generated",
        "rendered_submission_available",
        "upload_success",
        "submitted",
        "result_available",
        "feedback_ingested",
        "blocker",
        "privacy result",
        "git status",
    ]:
        lines.append(f"- {key}: `{status.get(key)}`")
    lines.append("")
    report_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"SITE_AUTO_STATUS_JSON={report_json.as_posix()}")
    return 0 if not status.get("blocker") else 1


if __name__ == "__main__":
    raise SystemExit(main())
