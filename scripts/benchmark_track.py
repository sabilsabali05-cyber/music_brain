from __future__ import annotations

import argparse
import json
from pathlib import Path

from mido import MidiFile


def benchmark_track(track_folder: Path) -> dict[str, object]:
    report_path = track_folder / "analysis" / "job_report.json"
    midi_path = track_folder / "midi" / "full_mix.mid"

    if not report_path.exists():
        raise FileNotFoundError(f"Missing job report: {report_path.as_posix()}")
    if not midi_path.exists():
        raise FileNotFoundError(f"Missing MIDI: {midi_path.as_posix()}")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    midi = MidiFile(str(midi_path))

    midi_track_count = len(midi.tracks)
    midi_message_count = sum(len(track) for track in midi.tracks)
    note_count = sum(
        1
        for track in midi.tracks
        for message in track
        if getattr(message, "type", "") == "note_on" and getattr(message, "velocity", 0) > 0
    )

    latencies = report.get("latency_seconds") or {}
    result = {
        "track_id": report.get("track_id"),
        "status": report.get("status"),
        "provider_used": report.get("provider_used"),
        "backend": report.get("backend"),
        "duration_seconds": report.get("duration_seconds"),
        "transcription_latency_seconds": latencies.get("transcription"),
        "total_latency_seconds": latencies.get("total"),
        "midi_file_size_bytes": midi_path.stat().st_size,
        "midi_track_count": midi_track_count,
        "midi_message_count": midi_message_count,
        "note_on_count": note_count,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Print basic benchmark stats for a completed track.")
    parser.add_argument("track_folder", help="Path to track folder (e.g., library/trk_...).")
    args = parser.parse_args()

    benchmark = benchmark_track(Path(args.track_folder))
    print(f"track_id: {benchmark['track_id']}")
    print(f"status: {benchmark['status']}")
    print(f"provider_used: {benchmark['provider_used']}")
    print(f"backend: {benchmark['backend']}")
    print(f"duration_seconds: {benchmark['duration_seconds']}")
    print(f"transcription_latency_seconds: {benchmark['transcription_latency_seconds']}")
    print(f"total_latency_seconds: {benchmark['total_latency_seconds']}")
    print(f"midi_file_size_bytes: {benchmark['midi_file_size_bytes']}")
    print(f"midi_track_count: {benchmark['midi_track_count']}")
    print(f"midi_message_count: {benchmark['midi_message_count']}")
    print(f"note_on_count: {benchmark['note_on_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
