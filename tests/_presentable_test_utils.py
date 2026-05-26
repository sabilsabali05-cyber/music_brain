from __future__ import annotations

import json
from pathlib import Path

from mido import Message, MetaMessage, MidiFile, MidiTrack


def build_test_midi(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    midi = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    midi.tracks.append(track)
    track.append(MetaMessage("set_tempo", tempo=500000, time=0))
    notes = [60, 64, 67, 69, 67, 64, 62, 60]
    for note in notes:
        track.append(Message("note_on", note=note, velocity=90, time=120))
        track.append(Message("note_off", note=note, velocity=0, time=180))
    track.append(MetaMessage("end_of_track", time=0))
    midi.save(path.as_posix())


def write_local_config(root: Path, midi_path: Path, training_allowed: bool = False, candidate_count: int = 8) -> Path:
    cfg = root / "config" / "presentable_composition_from_draft.local.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(
        json.dumps(
            {
                "local_input_midi_path": midi_path.as_posix(),
                "training_allowed": training_allowed,
                "candidate_count": candidate_count,
                "seed": 1337,
            },
            indent=2,
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return cfg
