from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def _load_manifest(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_manifest(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _run_command(command: list[str]) -> list[str]:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        text = "\n".join(part for part in [result.stdout, result.stderr] if part).strip()
        raise RuntimeError(text or f"Command failed: {' '.join(command)}")
    return [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]


def _parse_prefixed_line(lines: list[str], prefix: str) -> str | None:
    for line in lines:
        if line.startswith(prefix):
            return line[len(prefix) :]
    return None


def _update_step(manifest: dict[str, object], step: str, status: str, *, reason: str | None = None) -> None:
    steps = manifest.get("steps", {})
    if not isinstance(steps, dict):
        steps = {}
        manifest["steps"] = steps
    now = datetime.now(timezone.utc).isoformat()
    payload: dict[str, object] = {"status": status, "updated_at": now}
    if reason:
        payload["reason"] = reason
    steps[step] = payload


def _step_status(manifest: dict[str, object], step: str) -> str | None:
    steps = manifest.get("steps", {})
    if not isinstance(steps, dict):
        return None
    payload = steps.get(step)
    if not isinstance(payload, dict):
        return None
    value = payload.get("status")
    return str(value) if value is not None else None


def process_performance_manifest(
    manifest_path: Path,
    *,
    max_windows: int = 3,
    resume: bool = False,
    force_analysis: bool = False,
    force_segmentation: bool = False,
    no_stitch: bool = False,
    allow_partial_stitch: bool = False,
) -> dict[str, object]:
    manifest = _load_manifest(manifest_path)
    source_path = Path(str(manifest.get("source_path", "")))
    if not source_path.exists():
        raise FileNotFoundError(f"Source audio missing: {source_path}")

    analysis_done = bool(manifest.get("analysis_path"))
    segmentation_done = bool(manifest.get("segments_manifest_path"))

    current_stage = "analysis"
    try:
        if force_analysis or not (resume and analysis_done):
            lines = _run_command(
                [
                    "python",
                    "scripts/analyze_audio_structure.py",
                    source_path.as_posix(),
                    "--backend",
                    "modal_librosa",
                    "--candidate-density",
                    "dense",
                    "--peak-pick-threshold",
                    "0.40",
                    "--min-boundary-distance-seconds",
                    "8.0",
                    "--max-candidates",
                    "24",
                ]
            )
            analysis_path = _parse_prefixed_line(lines, "ANALYSIS_PATH=")
            if not analysis_path:
                raise RuntimeError("ANALYSIS_PATH not found in analysis output.")
            manifest["analysis_path"] = analysis_path
            _update_step(manifest, "analysis", "success")
            _save_manifest(manifest_path, manifest)

        current_stage = "segmentation"
        if force_segmentation or not (resume and segmentation_done):
            lines = _run_command(
                [
                    "python",
                    "scripts/segment_audio.py",
                    source_path.as_posix(),
                    "--strategy",
                    "audio_structure",
                    "--target-window-seconds",
                    "60",
                    "--max-window-seconds",
                    "90",
                    "--context-seconds",
                    "5",
                ]
            )
            segments_manifest_path = _parse_prefixed_line(lines, "MANIFEST_PATH=")
            if not segments_manifest_path:
                raise RuntimeError("MANIFEST_PATH not found in segmentation output.")
            manifest["segments_manifest_path"] = segments_manifest_path
            _update_step(manifest, "segmentation", "success")
            _save_manifest(manifest_path, manifest)

        segments_manifest_path = Path(str(manifest.get("segments_manifest_path", "")))
        if not segments_manifest_path.exists():
            raise FileNotFoundError(f"Segments manifest missing: {segments_manifest_path}")

        current_stage = "transcription"
        if not (resume and _step_status(manifest, "transcription") == "success"):
            _run_command(
                [
                    "python",
                    "scripts/transcribe_windows.py",
                    segments_manifest_path.as_posix(),
                    "--max-windows",
                    str(max_windows),
                ]
            )
            _update_step(manifest, "transcription", "success")
            _save_manifest(manifest_path, manifest)

        current_stage = "benchmark"
        reports = manifest.get("reports", {})
        if not isinstance(reports, dict):
            reports = {}
            manifest["reports"] = reports
        if not (resume and _step_status(manifest, "benchmark") == "success"):
            benchmark_lines = _run_command(["python", "scripts/benchmark_segments.py", segments_manifest_path.as_posix()])
            benchmark_summary: dict[str, object] = {}
            for line in benchmark_lines:
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                benchmark_summary[key.strip()] = value.strip()
            reports["benchmark_summary"] = benchmark_summary
            _update_step(manifest, "benchmark", "success")
            _save_manifest(manifest_path, manifest)

        current_stage = "review"
        if not (resume and _step_status(manifest, "review") == "success"):
            review_lines = _run_command(["python", "scripts/review_segments.py", segments_manifest_path.as_posix()])
            review_path = _parse_prefixed_line(review_lines, "REVIEW_REPORT_PATH=")
            reports["review_report_path"] = review_path
            _update_step(manifest, "review", "success")
            _save_manifest(manifest_path, manifest)

        current_stage = "stitch"
        if not no_stitch and not (resume and _step_status(manifest, "stitch") == "success"):
            windows_payload = _load_manifest(segments_manifest_path).get("transcription_windows", [])
            pending = [
                window
                for window in windows_payload
                if isinstance(window, dict) and str(window.get("status", "pending")) != "success"
            ]
            if pending and not allow_partial_stitch:
                manifest["merged_midi_path"] = None
                _update_step(
                    manifest,
                    "stitch",
                    "skipped_incomplete_manifest",
                    reason="manifest has pending or failed windows",
                )
            else:
                stitch_command = ["python", "scripts/stitch_midi.py", segments_manifest_path.as_posix()]
                if allow_partial_stitch:
                    stitch_command.append("--allow-partial")
                stitch_lines = _run_command(stitch_command)
                merged_midi_path = _parse_prefixed_line(stitch_lines, "MERGED_MIDI_PATH=")
                if merged_midi_path:
                    manifest["merged_midi_path"] = merged_midi_path
                _update_step(manifest, "stitch", "success")
        elif no_stitch:
            _update_step(manifest, "stitch", "skipped_no_stitch")

        manifest["status"] = "processed"
        _save_manifest(manifest_path, manifest)
        return manifest
    except Exception as exc:  # noqa: BLE001
        _update_step(manifest, current_stage, "failed")
        manifest["status"] = "failed"
        manifest["last_error"] = f"{exc.__class__.__name__}: {exc}"
        _save_manifest(manifest_path, manifest)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Process one ingested performance manifest through safe staged flow.")
    parser.add_argument("performance_manifest", help="Path to performances/library/<id>/performance_manifest.json")
    parser.add_argument("--max-windows", type=int, default=3)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--force-analysis", action="store_true")
    parser.add_argument("--force-segmentation", action="store_true")
    parser.add_argument("--no-stitch", action="store_true")
    parser.add_argument("--allow-partial-stitch", action="store_true")
    args = parser.parse_args()

    manifest = process_performance_manifest(
        Path(args.performance_manifest),
        max_windows=args.max_windows,
        resume=args.resume,
        force_analysis=args.force_analysis,
        force_segmentation=args.force_segmentation,
        no_stitch=args.no_stitch,
        allow_partial_stitch=args.allow_partial_stitch,
    )
    print(f"PERFORMANCE_STATUS={manifest.get('status')}")
    print(f"SEGMENTS_MANIFEST_PATH={manifest.get('segments_manifest_path')}")
    print(f"MERGED_MIDI_PATH={manifest.get('merged_midi_path')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
