from __future__ import annotations

from pathlib import Path

from mido import Message, MidiFile, MidiTrack

from features.local_rendering.chordpotion_output_analysis import analyze_transformed_midi


def _make_midi(path: Path, note_count: int) -> None:
    midi = MidiFile()
    track = MidiTrack()
    midi.tracks.append(track)
    for i in range(note_count):
        note = 60 + (i % 7)
        track.append(Message("note_on", note=note, velocity=90, time=30))
        track.append(Message("note_off", note=note, velocity=0, time=30))
    midi.save(str(path))


def test_output_analysis_penalizes_overbusy_patterns(tmp_path: Path) -> None:
    dense = tmp_path / "dense.mid"
    sparse = tmp_path / "sparse.mid"
    _make_midi(dense, 160)
    _make_midi(sparse, 16)
    dense_analysis = analyze_transformed_midi(dense)
    sparse_analysis = analyze_transformed_midi(sparse)
    assert dense_analysis.overbusy_penalty >= sparse_analysis.overbusy_penalty
    assert dense_analysis.note_count > sparse_analysis.note_count
