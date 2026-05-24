from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts import internal_beat_loop
from scripts import internal_beat_loop_status
from scripts import stop_internal_beat_loop


def test_loop_output_path_ignored_and_not_tracked() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    check_one = subprocess.run(
        ["git", "check-ignore", "outputs/internal_beat_loop/loop_status.json"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    check_two = subprocess.run(
        ["git", "check-ignore", "outputs/internal_beat_loop/attempts"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    tracked = subprocess.run(
        ["git", "ls-files", "outputs/internal_beat_loop"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert check_one.returncode == 0
    assert check_two.returncode == 0
    assert tracked.stdout.strip() == ""


def test_status_command_works_without_running_loop(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(internal_beat_loop_status, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(
        internal_beat_loop_status,
        "STATUS_PATH",
        tmp_path / "outputs" / "internal_beat_loop" / "loop_status.json",
    )
    monkeypatch.setattr(internal_beat_loop_status, "OUTPUT_DIR", tmp_path / "outputs" / "internal_beat_loop")
    monkeypatch.setattr(internal_beat_loop_status, "ATTEMPTS_DIR", tmp_path / "outputs" / "internal_beat_loop" / "attempts")
    monkeypatch.setattr(internal_beat_loop_status, "_ignored_by_git", lambda: True)

    exit_code = internal_beat_loop_status.main()
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "running=false" in out
    assert "attempts_count=0" in out
    assert "ignored_by_git=true" in out


def test_stop_command_fails_safely_if_pid_missing(tmp_path: Path, monkeypatch) -> None:
    status_path = tmp_path / "outputs" / "internal_beat_loop" / "loop_status.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps({"running": True, "total_attempts": 1}, indent=2) + "\n", encoding="utf-8")

    monkeypatch.setattr(stop_internal_beat_loop, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(stop_internal_beat_loop, "STATUS_PATH", status_path)

    exit_code = stop_internal_beat_loop.main([])
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    assert exit_code == 1
    assert payload["stopped"] is True
    assert payload["running"] is False
    assert payload["latest_error"] == "stop_requested_pid_missing"


def test_loop_recovers_from_per_iteration_failure(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(internal_beat_loop, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(internal_beat_loop.time, "sleep", lambda _: None)

    class _Result:
        def __init__(self, returncode: int, stderr: str = "", stdout: str = "") -> None:
            self.returncode = returncode
            self.stderr = stderr
            self.stdout = stdout

    results = [_Result(1, stderr="first failure"), _Result(0, stdout="second success")]

    def _fake_run_pipeline():
        return results.pop(0)

    monkeypatch.setattr(internal_beat_loop, "_run_pipeline", _fake_run_pipeline)

    exit_code = internal_beat_loop.run_loop(interval_seconds=1, max_iterations=2)
    assert exit_code == 0

    status_path = tmp_path / "outputs" / "internal_beat_loop" / "loop_status.json"
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    assert payload["total_attempts"] == 2
    assert payload["failed_attempts"] == 1
    assert payload["successful_attempts"] == 1
    assert payload["latest_error"] == ""
    assert payload["running"] is False


def test_no_generated_outputs_tracked() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    tracked = subprocess.run(
        ["git", "ls-files", "outputs/internal_beat_loop/attempts"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert tracked.stdout.strip() == ""
