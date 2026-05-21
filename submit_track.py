from __future__ import annotations

import argparse
import json
from pathlib import Path

from music_brain.audio import AudioProcessingError, checksum_sha256, convert_to_normalized_wav, wav_duration_seconds
from music_brain.config import load_config
from music_brain.ids import new_track_id
from music_brain.preflight import run_preflight
from music_brain.schemas import ArtifactPaths, ErrorDetails, JobReport, LatencySeconds, PreflightReport
from music_brain.storage import TrackStorage
from music_brain.telemetry import StageTimer
from music_brain.transcription import create_transcriber
from music_brain.transcription.base import TranscriptionRequest


def _path_text(path: Path) -> str:
    return path.resolve().as_posix()


def track_dir_from_report(report: JobReport) -> Path:
    return Path(report.artifacts.job_report).resolve().parent.parent


def run_submission(input_audio: Path) -> JobReport:
    config = load_config()
    timer = StageTimer()
    current_stage = "init"

    track_id = new_track_id()
    storage = TrackStorage(config.library_root)
    paths = storage.build_paths(track_id=track_id, input_filename=input_audio.name)
    storage.ensure_directories(paths)

    report = JobReport(
        track_id=track_id,
        input_filename=input_audio.name,
        provider_requested=config.provider_requested,
        provider_used="none",
        fallback_used=False,
        fallback_reason=None,
        model_version="",
        backend=config.backend,
        status="failed",
        artifacts=ArtifactPaths(
            input_audio=_path_text(paths.input_audio),
            normalized_audio=_path_text(paths.normalized_audio),
            full_mix_midi=_path_text(paths.full_mix_midi),
            job_report=_path_text(paths.job_report),
        ),
        latency_seconds=LatencySeconds(),
        error=None,
    )

    try:
        if not input_audio.exists():
            raise FileNotFoundError(f"Input audio does not exist: {input_audio}")

        current_stage = "checksum"
        with timer.measure("checksum"):
            report.checksum = checksum_sha256(input_audio)

        current_stage = "copy_input"
        with timer.measure("copy_input"):
            storage.copy_input(input_audio, paths.input_audio)

        current_stage = "ffmpeg_convert"
        with timer.measure("ffmpeg_convert"):
            convert_to_normalized_wav(paths.input_audio, paths.normalized_audio)
        report.duration_seconds = wav_duration_seconds(paths.normalized_audio)

        current_stage = "transcription"
        with timer.measure("transcription"):
            transcriber = create_transcriber(
                provider_requested=config.provider_requested,
                backend=config.backend,
                modal_endpoint=config.modal_endpoint,
            )
            result = transcriber.transcribe(
                TranscriptionRequest(
                    track_id=track_id,
                    normalized_audio_path=paths.normalized_audio,
                    output_midi_path=paths.full_mix_midi,
                )
            )

        report.provider_used = result.provider_used
        report.fallback_used = result.fallback_used
        report.fallback_reason = result.fallback_reason
        report.model_version = result.model_version
        report.backend = result.backend
        report.status = "success"
        report.error = None
    except Exception as exc:  # noqa: BLE001
        if isinstance(exc, AudioProcessingError):
            message = str(exc)
        else:
            message = str(exc) or exc.__class__.__name__
        report.status = "failed"
        report.error = ErrorDetails(
            stage=current_stage,
            message=message,
            exception_type=exc.__class__.__name__,
        )
    finally:
        report.latency_seconds = LatencySeconds(
            checksum=timer.durations.get("checksum", 0.0),
            copy_input=timer.durations.get("copy_input", 0.0),
            ffmpeg_convert=timer.durations.get("ffmpeg_convert", 0.0),
            transcription=timer.durations.get("transcription", 0.0),
            total=timer.total_seconds(),
        )
        paths.analysis_dir.mkdir(parents=True, exist_ok=True)
        paths.job_report.write_text(
            json.dumps(report.model_dump(), indent=2),
            encoding="utf-8",
        )

    return report


def format_success_output(report: JobReport) -> str:
    return "\n".join(
        [
            "Submission result:",
            f"  track_id: {report.track_id}",
            f"  status: {report.status}",
            f"  provider_used: {report.provider_used}",
            f"  backend: {report.backend}",
            f"  midi_path: {report.artifacts.full_mix_midi}",
            f"  job_report: {report.artifacts.job_report}",
            f"  total_latency_seconds: {report.latency_seconds.total:.3f}",
        ]
    )


def format_failure_output(report: JobReport) -> str:
    stage = report.error.stage if report.error is not None else "unknown"
    message = report.error.message if report.error is not None else "Unknown failure"
    return "\n".join(
        [
            "Submission result:",
            f"  status: {report.status}",
            f"  failing_stage: {stage}",
            f"  error_message: {message}",
            f"  job_report: {report.artifacts.job_report}",
        ]
    )


def format_preflight_output(report: PreflightReport) -> str:
    lines = [
        "Preflight result:",
        f"  overall_ok: {report.ok}",
        f"  python_version: {report.python_version}",
        f"  cwd: {report.cwd}",
        f"  provider: {report.provider}",
        f"  backend: {report.backend}",
        f"  library_root: {report.library_root}",
        "  checks:",
    ]
    for check in report.checks:
        status = "PASS" if check.ok else "FAIL"
        lines.append(f"    - [{status}] {check.name}: {check.message}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit one audio track into music_brain V2 MVP.")
    parser.add_argument("input_audio", nargs="?", type=Path, help="Path to an audio file (mp3/wav/etc).")
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Run environment and backend readiness checks without submitting audio.",
    )
    parser.add_argument(
        "--print-track-dir",
        action="store_true",
        help="Print machine-readable TRACK_DIR/JOB_REPORT/MIDI_PATH lines for automation.",
    )
    args = parser.parse_args()

    if args.preflight:
        preflight_report = run_preflight()
        print(format_preflight_output(preflight_report))
        raise SystemExit(0 if preflight_report.ok else 1)

    if args.input_audio is None:
        parser.error("input_audio is required unless --preflight is used")

    report = run_submission(args.input_audio)
    if report.status == "success":
        print(format_success_output(report))
    else:
        print(format_failure_output(report))
        print("\nFull report JSON:")
        print(json.dumps(report.model_dump(), indent=2))
    if args.print_track_dir:
        print(f"TRACK_DIR={track_dir_from_report(report).as_posix()}")
        print(f"JOB_REPORT={report.artifacts.job_report}")
        print(f"MIDI_PATH={report.artifacts.full_mix_midi}")
    if report.status == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
