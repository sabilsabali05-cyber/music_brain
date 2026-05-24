from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
STATUS_PATH = ROOT_DIR / "outputs" / "internal_beat_loop" / "loop_status.json"
EXPECTED_SCRIPT_TOKEN = "scripts/internal_beat_loop.py"


def _iso_now() -> str:
    return datetime.now(UTC).isoformat()


def _read_status() -> dict[str, Any]:
    if not STATUS_PATH.exists():
        return {}
    try:
        payload = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_status(payload: dict[str, Any]) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _get_command_line(pid: int) -> str:
    if pid <= 0:
        return ""
    if os.name == "nt":
        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"(Get-CimInstance Win32_Process -Filter \"ProcessId={pid}\").CommandLine",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        return (proc.stdout or "").strip()
    return ""


def _looks_like_loop_process(command_line: str) -> bool:
    normalized = command_line.replace("\\", "/").lower()
    return EXPECTED_SCRIPT_TOKEN in normalized


def _graceful_stop(pid: int) -> bool:
    if not _is_running(pid):
        return True
    try:
        os.kill(pid, signal.SIGINT)
    except OSError:
        return not _is_running(pid)
    deadline = time.time() + 6.0
    while time.time() < deadline:
        if not _is_running(pid):
            return True
        time.sleep(0.2)
    return False


def _terminate_stop(pid: int) -> bool:
    if not _is_running(pid):
        return True
    if os.name == "nt":
        proc = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T"],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            return not _is_running(pid)
        proc_force = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            check=False,
        )
        return proc_force.returncode == 0 or not _is_running(pid)
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return not _is_running(pid)
    deadline = time.time() + 4.0
    while time.time() < deadline:
        if not _is_running(pid):
            return True
        time.sleep(0.2)
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        return not _is_running(pid)
    return not _is_running(pid)


def main(argv: list[str] | None = None) -> int:
    _ = argv
    status = _read_status()
    pid_value = status.get("pid")
    pid = int(pid_value) if isinstance(pid_value, int) or (isinstance(pid_value, str) and pid_value.isdigit()) else 0
    status["stop_requested_at"] = _iso_now()
    status["stopped"] = True

    if pid <= 0:
        status["running"] = False
        status["latest_error"] = "stop_requested_pid_missing"
        _write_status(status)
        print("INTERNAL_BEAT_LOOP_STOPPED running=false pid=missing reason=pid_missing")
        return 1

    command_line = _get_command_line(pid)
    if command_line and not _looks_like_loop_process(command_line):
        status["running"] = _is_running(pid)
        status["latest_error"] = "stop_refused_pid_command_mismatch"
        _write_status(status)
        print(f"INTERNAL_BEAT_LOOP_STOP_REFUSED pid={pid} reason=command_mismatch")
        return 1

    stopped = _graceful_stop(pid)
    method = "graceful"
    if not stopped:
        stopped = _terminate_stop(pid)
        method = "terminate"

    status["running"] = _is_running(pid)
    status["stopped"] = True
    status["stopped_at"] = _iso_now()
    status["stop_method"] = method
    if stopped:
        status["latest_error"] = ""
    elif not status.get("latest_error"):
        status["latest_error"] = "stop_failed_process_still_running"
    _write_status(status)
    print(f"INTERNAL_BEAT_LOOP_STOP_RESULT running={str(status['running']).lower()} pid={pid} method={method}")
    return 0 if stopped else 1


if __name__ == "__main__":
    raise SystemExit(main())
