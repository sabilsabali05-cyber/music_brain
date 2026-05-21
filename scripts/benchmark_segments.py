from __future__ import annotations

import argparse
import json
from pathlib import Path

from mido import MidiFile


def benchmark_segments(manifest_path: Path) -> dict[str, float | int]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    musical_segments = manifest.get("musical_segments", [])
    windows = manifest.get("transcription_windows", [])
    performance_duration = float(manifest.get("duration_seconds", 0.0) or 0.0)

    successful_windows = [w for w in windows if isinstance(w, dict) and w.get("status") == "success"]
    failed_windows = [w for w in windows if isinstance(w, dict) and w.get("status") == "failed"]

    represented_duration = sum(
        max(0.0, float(w.get("core_end_seconds", 0.0)) - float(w.get("core_start_seconds", 0.0)))
        for w in windows
        if isinstance(w, dict)
    )

    total_transcription_latency = 0.0
    total_midi_bytes = 0
    total_note_on_count = 0

    for window in successful_windows:
        job_report_path = window.get("job_report")
        if job_report_path and Path(str(job_report_path)).exists():
            report = json.loads(Path(str(job_report_path)).read_text(encoding="utf-8"))
            latencies = report.get("latency_seconds") or {}
            total_transcription_latency += float(latencies.get("transcription", 0.0) or 0.0)

        midi_path = window.get("midi_path")
        if midi_path and Path(str(midi_path)).exists():
            midi_file = Path(str(midi_path))
            total_midi_bytes += midi_file.stat().st_size
            midi = MidiFile(str(midi_file))
            total_note_on_count += sum(
                1
                for track in midi.tracks
                for message in track
                if getattr(message, "type", "") == "note_on" and getattr(message, "velocity", 0) > 0
            )

    average_latency = (
        total_transcription_latency / len(successful_windows) if successful_windows else 0.0
    )
    coverage_ratio = represented_duration / performance_duration if performance_duration > 0 else 0.0

    return {
        "total_musical_segments": len(musical_segments),
        "total_transcription_windows": len(windows),
        "successful_windows": len(successful_windows),
        "failed_windows": len(failed_windows),
        "represented_audio_duration_seconds": round(represented_duration, 6),
        "total_transcription_latency_seconds": round(total_transcription_latency, 6),
        "average_transcription_latency_seconds": round(average_latency, 6),
        "total_midi_bytes": int(total_midi_bytes),
        "total_note_on_count": int(total_note_on_count),
        "segment_window_coverage_ratio": round(coverage_ratio, 6),
        "segment_window_coverage_percent": round(coverage_ratio * 100.0, 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize long-audio segment/window transcription outcomes.")
    parser.add_argument("manifest_path", help="Path to segments manifest JSON.")
    args = parser.parse_args()

    manifest_path = Path(args.manifest_path)
    summary = benchmark_segments(manifest_path)
    print(f"manifest: {manifest_path.resolve().as_posix()}")
    for key, value in summary.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
