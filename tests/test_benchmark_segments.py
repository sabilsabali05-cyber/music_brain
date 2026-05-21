from __future__ import annotations

import json
from pathlib import Path

from mido import Message, MidiFile, MidiTrack

from scripts.benchmark_segments import benchmark_segments


def test_benchmark_segments_summarizes_manifest_outputs(tmp_path: Path) -> None:
    track_folder = tmp_path / "library" / "trk_1"
    (track_folder / "analysis").mkdir(parents=True)
    (track_folder / "midi").mkdir(parents=True)

    report = {"latency_seconds": {"transcription": 12.5, "total": 13.0}}
    report_path = track_folder / "analysis" / "job_report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    midi = MidiFile()
    midi_track = MidiTrack()
    midi_track.append(Message("note_on", note=60, velocity=50, time=0))
    midi_track.append(Message("note_off", note=60, velocity=0, time=120))
    midi.tracks.append(midi_track)
    midi_path = track_folder / "midi" / "full_mix.mid"
    midi.save(midi_path)

    manifest = {
        "performance_id": "perf_1",
        "duration_seconds": 60.0,
        "musical_segments": [{"segment_id": "seg_0000"}],
        "transcription_windows": [
            {
                "window_id": "win_0000",
                "status": "success",
                "core_start_seconds": 0.0,
                "core_end_seconds": 60.0,
                "job_report": report_path.as_posix(),
                "midi_path": midi_path.as_posix(),
            }
        ],
    }
    manifest_path = tmp_path / "segments_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    summary = benchmark_segments(manifest_path)

    assert summary["total_musical_segments"] == 1
    assert summary["total_transcription_windows"] == 1
    assert summary["successful_windows"] == 1
    assert summary["failed_windows"] == 0
    assert summary["represented_audio_duration_seconds"] == 60.0
    assert summary["total_transcription_latency_seconds"] == 12.5
    assert summary["total_midi_bytes"] > 0
    assert summary["total_note_on_count"] == 1
    assert summary["segment_window_coverage_percent"] == 100.0
