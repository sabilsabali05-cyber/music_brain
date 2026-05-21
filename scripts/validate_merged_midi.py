from __future__ import annotations

import argparse
from pathlib import Path

from mido import MidiFile


def validate_merged_midi(merged_midi_path: Path) -> dict[str, object]:
    if not merged_midi_path.exists():
        raise FileNotFoundError(f"Merged MIDI does not exist: {merged_midi_path}")
    midi = MidiFile(str(merged_midi_path))
    track_count = len(midi.tracks)
    message_count = sum(len(track) for track in midi.tracks)
    note_on_count = sum(
        1
        for track in midi.tracks
        for message in track
        if getattr(message, "type", "") == "note_on" and int(getattr(message, "velocity", 0)) > 0
    )
    if message_count <= 0 or note_on_count <= 0:
        raise RuntimeError("Merged MIDI is empty or has no note_on events.")
    return {
        "merged_midi_path": merged_midi_path.resolve().as_posix(),
        "tracks": track_count,
        "messages": message_count,
        "note_on_count": note_on_count,
        "status": "success",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate merged MIDI output.")
    parser.add_argument("merged_midi_path", help="Path to merged_performance.mid")
    args = parser.parse_args()
    summary = validate_merged_midi(Path(args.merged_midi_path))
    for key, value in summary.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
