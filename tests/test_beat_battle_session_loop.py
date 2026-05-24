from __future__ import annotations

import json
from pathlib import Path

from scripts.beat_battle_session_loop import (
    STATUS_TRAINING_SKIPPED,
    STATUS_WAITING_SUBMIT,
    run_session_once,
)


def _write_local_config(repo_root: Path) -> None:
    payload = {
        "site_name": "Beat Battle Ranked",
        "base_url": "https://example.invalid",
        "ranked_path": "/ranked",
        "user_handle": "tester",
    }
    config_path = repo_root / "config" / "beat_battle_ranked_site.local.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _prepare_round_folder(repo_root: Path, round_id: str = "round_001") -> None:
    folder = repo_root / "datasets_local" / "beat_battle_site" / "manual_round_sounds" / round_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "kick.wav").write_bytes(b"RIFF")


def _status_payload(repo_root: Path) -> dict:
    status_path = repo_root / "reports" / "beat_battle_site_automation" / "session_loop_status.json"
    assert status_path.exists()
    return json.loads(status_path.read_text(encoding="utf-8"))


def test_session_loop_safe_fails_when_local_config_missing(tmp_path: Path) -> None:
    exit_code = run_session_once(project_root=tmp_path, poll_seconds=1, max_wait_seconds=0)
    assert exit_code == 1
    status = _status_payload(tmp_path)
    assert status["blocker"] == "missing_local_site_config"
    assert status["status"] == "processing_round"


def test_session_loop_pauses_for_manual_submission(tmp_path: Path) -> None:
    _write_local_config(tmp_path)
    _prepare_round_folder(tmp_path, "round_002")

    def fake_run_script(project_root: Path, script_name: str, args: list[str]) -> tuple[int, str]:
        if script_name == "submit_beat_battle_entry.py":
            report_path = project_root / "reports" / "beat_battle_site_automation" / "submission_report.json"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(
                json.dumps(
                    {
                        "status": "stopped_pre_submit_manual_confirmation_required",
                        "submitted": False,
                        "upload_success": False,
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
        return 0, ""

    exit_code = run_session_once(
        project_root=tmp_path,
        poll_seconds=1,
        max_wait_seconds=0,
        run_script=fake_run_script,
    )
    assert exit_code == 0
    status = _status_payload(tmp_path)
    assert status["status"] == STATUS_WAITING_SUBMIT
    assert "Manual site submission required" in status["status_history"][-1]["message"]


def test_session_loop_marks_training_skipped_when_feedback_threshold_not_met(tmp_path: Path) -> None:
    _write_local_config(tmp_path)
    _prepare_round_folder(tmp_path, "round_003")
    snapshot_path = tmp_path / "artifacts" / "beat_battle_site" / "manual_result_snapshot.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(
        json.dumps({"round_id": "round_003", "result_available": True}, indent=2) + "\n",
        encoding="utf-8",
    )

    run_calls: list[str] = []

    def fake_run_script(project_root: Path, script_name: str, args: list[str]) -> tuple[int, str]:
        run_calls.append(script_name)
        if script_name == "submit_beat_battle_entry.py":
            report_path = project_root / "reports" / "beat_battle_site_automation" / "submission_report.json"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps({"status": "submitted", "submitted": True}, indent=2) + "\n", encoding="utf-8")
        return 0, ""

    exit_code = run_session_once(
        project_root=tmp_path,
        poll_seconds=1,
        max_wait_seconds=0,
        run_script=fake_run_script,
    )
    assert exit_code == 0
    status = _status_payload(tmp_path)
    assert status["status"] == STATUS_TRAINING_SKIPPED
    assert status["authorized_feedback_count"] == 0
    assert "train_beat_battle_site_ranker.py" not in run_calls
