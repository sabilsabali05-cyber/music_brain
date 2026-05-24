from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
STATUS_PATH = ROOT_DIR / "outputs" / "internal_beat_loop" / "loop_status.json"
OUTPUT_DIR = ROOT_DIR / "outputs" / "internal_beat_loop"
ATTEMPTS_DIR = OUTPUT_DIR / "attempts"
EXPECTED_SCRIPT_TOKEN = "scripts/internal_beat_loop.py"


def _read_status() -> dict[str, Any]:
    if not STATUS_PATH.exists():
        return {}
    try:
        payload = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _process_command_line(pid: int) -> str:
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


def _is_loop_pid(pid: int) -> bool:
    command = _process_command_line(pid)
    if not command:
        return False
    return EXPECTED_SCRIPT_TOKEN in command.replace("\\", "/").lower()


def _attempts_count(status: dict[str, Any]) -> int:
    value = status.get("total_attempts")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    if ATTEMPTS_DIR.exists():
        return sum(1 for p in ATTEMPTS_DIR.iterdir() if p.is_dir())
    return 0


def _last_success(status: dict[str, Any]) -> str:
    latest_error = str(status.get("latest_error", "")).strip()
    latest_output = str(status.get("latest_output_path", "")).strip()
    if latest_output and not latest_error:
        return latest_output
    if not ATTEMPTS_DIR.exists():
        return ""
    candidates = sorted([p for p in ATTEMPTS_DIR.iterdir() if p.is_dir()], key=lambda p: p.name, reverse=True)
    for attempt_dir in candidates:
        report = attempt_dir / "attempt_report.json"
        if not report.exists():
            continue
        try:
            payload = json.loads(report.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if payload.get("exit_code") == 0:
            return attempt_dir.relative_to(ROOT_DIR).as_posix()
    return ""


def _ignored_by_git() -> bool:
    for rel in ["outputs/internal_beat_loop/loop_status.json", "outputs/internal_beat_loop/attempts"]:
        proc = subprocess.run(["git", "check-ignore", rel], cwd=ROOT_DIR, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            return False
    return True


def main() -> int:
    status = _read_status()
    pid_value = status.get("pid")
    pid = int(pid_value) if isinstance(pid_value, int) or (isinstance(pid_value, str) and pid_value.isdigit()) else 0
    running = _is_running(pid) and _is_loop_pid(pid)

    started_at = str(status.get("started_at", "")).strip()
    attempts_count = _attempts_count(status)
    last_attempt = str(status.get("latest_output_path", "")).strip()
    last_success = _last_success(status)
    last_error = str(status.get("latest_error", "")).strip()

    print(f"running={str(running).lower()}")
    print(f"pid={pid if pid > 0 else ''}")
    print(f"started_at={started_at}")
    print(f"attempts_count={attempts_count}")
    print(f"last_attempt={last_attempt}")
    print(f"last_success={last_success}")
    print(f"last_error={last_error}")
    print(f"output_folder={OUTPUT_DIR.relative_to(ROOT_DIR).as_posix()}")
    print(f"ignored_by_git={str(_ignored_by_git()).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
