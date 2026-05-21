from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path


def load_manifest(manifest_path: Path) -> dict[str, object]:
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def save_manifest(manifest_path: Path, manifest: dict[str, object]) -> None:
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _parse_submit_output(stdout: str) -> dict[str, str | None]:
    parsed: dict[str, str | None] = {"track_folder": None, "job_report": None, "midi_path": None}
    for line in stdout.splitlines():
        text = line.strip()
        if text.startswith("TRACK_DIR="):
            parsed["track_folder"] = text.split("=", 1)[1]
        elif text.startswith("JOB_REPORT="):
            parsed["job_report"] = text.split("=", 1)[1]
        elif text.startswith("MIDI_PATH="):
            parsed["midi_path"] = text.split("=", 1)[1]
    return parsed


def submit_window(chunk_audio_path: str) -> tuple[bool, dict[str, str | None], str]:
    env = os.environ.copy()
    env["MUSIC_BRAIN_PROVIDER"] = "yourmt3"
    env["MUSIC_BRAIN_BACKEND"] = "modal"
    env["MUSIC_BRAIN_MT3_MODEL"] = "yourmt3"
    env["MUSIC_BRAIN_MODAL_GPU"] = "T4"

    command = ["python", "submit_track.py", chunk_audio_path, "--print-track-dir"]
    result = subprocess.run(command, capture_output=True, text=True, check=False, env=env)
    parsed = _parse_submit_output(result.stdout)
    combined_output = "\n".join(part for part in [result.stdout, result.stderr] if part)
    return result.returncode == 0, parsed, combined_output


def transcribe_windows(manifest_path: Path, *, max_windows: int | None, force: bool) -> dict[str, object]:
    manifest = load_manifest(manifest_path)
    windows = manifest.get("transcription_windows")
    if not isinstance(windows, list):
        raise RuntimeError("Manifest missing transcription_windows list")

    processed = 0
    for window in windows:
        if not isinstance(window, dict):
            continue

        if max_windows is not None and processed >= max_windows:
            break

        status = str(window.get("status", "pending"))
        if status == "success" and not force:
            continue

        chunk_audio_path = window.get("chunk_audio_path")
        if not chunk_audio_path:
            window["status"] = "failed"
            window["error"] = "Missing chunk_audio_path"
            processed += 1
            continue

        window["status"] = "running"
        save_manifest(manifest_path, manifest)

        ok, parsed, combined_output = submit_window(str(chunk_audio_path))
        if ok:
            window["status"] = "success"
            window["track_folder"] = parsed["track_folder"]
            window["job_report"] = parsed["job_report"]
            window["midi_path"] = parsed["midi_path"]
            window["error"] = None
        else:
            window["status"] = "failed"
            window["error"] = combined_output.strip() or "Unknown transcription failure"
        processed += 1

    save_manifest(manifest_path, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Transcribe windows listed in a segments manifest.")
    parser.add_argument("manifest_path", help="Path to segments_manifest.json")
    parser.add_argument("--max-windows", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    manifest_path = Path(args.manifest_path)
    manifest = transcribe_windows(manifest_path, max_windows=args.max_windows, force=args.force)
    windows = manifest.get("transcription_windows", [])
    success_count = sum(1 for w in windows if isinstance(w, dict) and w.get("status") == "success")
    failed_count = sum(1 for w in windows if isinstance(w, dict) and w.get("status") == "failed")
    print(f"manifest: {manifest_path.resolve().as_posix()}")
    print(f"success_windows: {success_count}")
    print(f"failed_windows: {failed_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
