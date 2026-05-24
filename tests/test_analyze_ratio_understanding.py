from __future__ import annotations

import json
from pathlib import Path

from scripts import analyze_ratio_understanding as script


def _create_simple_midi(path: Path) -> None:
    from mido import Message, MetaMessage, MidiFile, MidiTrack

    midi = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    midi.tracks.append(track)
    track.append(MetaMessage("set_tempo", tempo=500000, time=0))
    for _ in range(8):
        track.append(Message("note_on", note=60, velocity=90, time=0))
        track.append(Message("note_off", note=60, velocity=0, time=240))
    track.append(MetaMessage("end_of_track", time=0))
    path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(path.as_posix())


def test_analyze_ratio_understanding_writes_outputs(tmp_path: Path, monkeypatch) -> None:
    midi_path = tmp_path / "outputs" / "music_understanding_loop_v1" / "candidates" / "candidate_01.mid"
    _create_simple_midi(midi_path)
    monkeypatch.setattr(script, "ROOT_DIR", tmp_path)
    assert script.main() == 0
    jsonl_path = tmp_path / "datasets" / "ratio_understanding" / "ratio_observations.jsonl"
    report_path = tmp_path / "reports" / "ratio_understanding" / "ratio_understanding_report.json"
    assert jsonl_path.exists()
    assert report_path.exists()
    rows = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) >= 5
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["ratio_observations_count"] == len(rows)
    assert report["evidence_based_only"] is True

