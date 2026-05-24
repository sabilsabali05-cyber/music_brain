from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _iso_now() -> str:
    return datetime.now(UTC).isoformat()


def _safe_json_read(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT_DIR.resolve()).as_posix()
    except Exception:  # noqa: BLE001
        return path.as_posix()


def _new_run_id() -> str:
    return datetime.now(UTC).strftime("run_%Y%m%dT%H%M%SZ")


def _stop_requested(status_path: Path) -> bool:
    payload = _safe_json_read(status_path)
    return bool(payload.get("stopped") or payload.get("stop_requested"))


def _load_selected_candidate_path() -> str:
    report = _safe_json_read(ROOT_DIR / "reports" / "taste_learning" / "ranked_midi_candidates_report.json")
    selected = str(report.get("selected_candidate_path", "")).strip()
    return selected


def _run_pipeline() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT_DIR / "scripts" / "run_music_understanding_loop.py")],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=False,
    )


def _snapshot_artifacts(run_dir: Path) -> dict[str, str]:
    run_dir.mkdir(parents=True, exist_ok=True)
    copied: dict[str, str] = {}

    candidates_report = ROOT_DIR / "reports" / "taste_learning" / "ranked_midi_candidates_report.json"
    loop_status = ROOT_DIR / "reports" / "integration" / "music_understanding_loop_status.json"
    generation_report = ROOT_DIR / "outputs" / "music_understanding_loop_v1" / "generation_report.json"

    for source in (candidates_report, loop_status, generation_report):
        if source.exists():
            dest = run_dir / source.name
            dest.write_bytes(source.read_bytes())
            copied[source.name] = _repo_rel(dest)

    selected_path = _load_selected_candidate_path()
    if selected_path:
        selected_abs = ROOT_DIR / selected_path
        if selected_abs.exists() and selected_abs.suffix.lower() in {".mid", ".midi", ".json", ".md", ".txt"}:
            selected_dest = run_dir / selected_abs.name
            selected_dest.write_bytes(selected_abs.read_bytes())
            copied["selected_artifact"] = _repo_rel(selected_dest)

    return copied


def run_loop(interval_seconds: int, max_iterations: int | None) -> int:
    loop_root = ROOT_DIR / "outputs" / "internal_beat_loop"
    attempts_root = loop_root / "attempts"
    status_path = loop_root / "loop_status.json"
    attempts_root.mkdir(parents=True, exist_ok=True)

    status: dict[str, Any] = {
        "loop_id": "internal_beat_loop_v1",
        "started_at": _iso_now(),
        "running": True,
        "pid": os.getpid(),
        "interval_seconds": interval_seconds,
        "total_attempts": 0,
        "successful_attempts": 0,
        "failed_attempts": 0,
        "latest_run_id": "",
        "latest_output_path": "",
        "latest_error": "",
        "latest_finished_at": "",
        "stopped": False,
        "stop_requested_at": "",
    }
    _write_json(status_path, status)

    iteration = 0
    while True:
        if _stop_requested(status_path):
            status["stopped"] = True
            status["running"] = False
            status["stop_requested_at"] = _safe_json_read(status_path).get("stop_requested_at", _iso_now())
            break

        if max_iterations is not None and iteration >= max_iterations:
            break

        started = time.time()
        run_id = _new_run_id()
        run_dir = attempts_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        run_log = run_dir / "pipeline.log"
        run_meta = run_dir / "attempt_report.json"

        result = _run_pipeline()
        run_log.write_text(
            "\n".join(
                [
                    "=== STDOUT ===",
                    result.stdout.rstrip(),
                    "",
                    "=== STDERR ===",
                    result.stderr.rstrip(),
                    "",
                ]
            ).strip()
            + "\n",
            encoding="utf-8",
        )

        status["total_attempts"] = int(status.get("total_attempts", 0)) + 1
        status["latest_run_id"] = run_id
        status["latest_output_path"] = _repo_rel(run_dir)
        status["latest_finished_at"] = _iso_now()

        attempt_payload: dict[str, Any] = {
            "run_id": run_id,
            "started_at": datetime.fromtimestamp(started, tz=UTC).isoformat(),
            "finished_at": _iso_now(),
            "exit_code": result.returncode,
            "run_dir": _repo_rel(run_dir),
            "policy": {
                "internal_only": True,
                "no_site_automation": True,
                "no_rendered_audio_exported": True,
            },
            "copied_artifacts": {},
        }

        if result.returncode == 0:
            status["successful_attempts"] = int(status.get("successful_attempts", 0)) + 1
            status["latest_error"] = ""
            attempt_payload["copied_artifacts"] = _snapshot_artifacts(run_dir)
        else:
            status["failed_attempts"] = int(status.get("failed_attempts", 0)) + 1
            error_tail = (result.stderr or result.stdout).strip().splitlines()
            status["latest_error"] = error_tail[-1][:300] if error_tail else "pipeline_failed"
            attempt_payload["error"] = status["latest_error"]

        _write_json(run_meta, attempt_payload)
        _write_json(status_path, status)

        print(
            f"INTERNAL_BEAT_LOOP iteration={status['total_attempts']} "
            f"success={status['successful_attempts']} failed={status['failed_attempts']} "
            f"latest={status['latest_output_path']}"
        )
        sys.stdout.flush()

        elapsed = time.time() - started
        sleep_for = max(0.0, float(interval_seconds) - elapsed)
        remaining = sleep_for
        while remaining > 0:
            if _stop_requested(status_path):
                status["stopped"] = True
                status["running"] = False
                status["stop_requested_at"] = _safe_json_read(status_path).get("stop_requested_at", _iso_now())
                remaining = 0
                break
            step = min(1.0, remaining)
            time.sleep(step)
            remaining -= step
        if status.get("stopped"):
            break
        iteration += 1

    status["running"] = False
    status["stopped_at"] = _iso_now()
    _write_json(status_path, status)
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run continuous internal-only beat generation attempts.")
    parser.add_argument("--interval-seconds", type=int, default=120, help="Seconds between attempt starts.")
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Optional cap for local testing. Omit for continuous mode.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    if args.interval_seconds <= 0:
        raise SystemExit("--interval-seconds must be > 0")
    try:
        return run_loop(interval_seconds=args.interval_seconds, max_iterations=args.max_iterations)
    except KeyboardInterrupt:
        print("INTERNAL_BEAT_LOOP stopped_by=keyboard_interrupt")
        return 130
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
