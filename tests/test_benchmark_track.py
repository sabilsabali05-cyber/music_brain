from __future__ import annotations

import json
from pathlib import Path

from mido import Message, MidiFile, MidiTrack

from scripts.benchmark_track import benchmark_track


def test_benchmark_track_reads_report_and_midi(tmp_path: Path) -> None:
    track_folder = tmp_path / "library" / "trk_test"
    (track_folder / "analysis").mkdir(parents=True)
    (track_folder / "midi").mkdir(parents=True)

    report = {
        "track_id": "trk_test",
        "status": "success",
        "provider_used": "yourmt3",
        "backend": "modal",
        "duration_seconds": 12.3,
        "latency_seconds": {"transcription": 4.2, "total": 5.1},
    }
    (track_folder / "analysis" / "job_report.json").write_text(json.dumps(report), encoding="utf-8")

    midi = MidiFile()
    t = MidiTrack()
    t.append(Message("program_change", program=0, time=0))
    t.append(Message("note_on", note=60, velocity=50, time=0))
    t.append(Message("note_off", note=60, velocity=0, time=120))
    t.append(Message("note_on", note=62, velocity=45, time=0))
    t.append(Message("note_off", note=62, velocity=0, time=120))
    midi.tracks.append(t)
    midi.save(track_folder / "midi" / "full_mix.mid")

    result = benchmark_track(track_folder)

    assert result["track_id"] == "trk_test"
    assert result["status"] == "success"
    assert result["provider_used"] == "yourmt3"
    assert result["backend"] == "modal"
    assert result["duration_seconds"] == 12.3
    assert result["transcription_latency_seconds"] == 4.2
    assert result["total_latency_seconds"] == 5.1
    assert result["midi_file_size_bytes"] > 0
    assert result["midi_track_count"] == 1
    assert result["midi_message_count"] == 6
    assert result["note_on_count"] == 2
