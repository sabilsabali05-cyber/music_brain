from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from mido import Message, MidiFile, MidiTrack

ROOT_DIR = Path(__file__).resolve().parent.parent
TRACK_FILES = {"drums": "ballad_drums.mid", "bass": "ballad_bass.mid", "chords": "ballad_chords.mid", "lead": "ballad_lead.mid", "texture": "ballad_texture.mid"}
SOURCE_OUTPUT = ROOT_DIR / "outputs" / "ballad_2min_v1"
TARGET_OUTPUT = ROOT_DIR / "outputs" / "ballad_2min_v2_review_regen"


def _write_simple_midi(path: Path, note: int, channel: int) -> None:
    midi = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    midi.tracks.append(track)
    track.append(Message("program_change", program=0, channel=channel, time=0))
    for _ in range(16):
        track.append(Message("note_on", note=note, velocity=82, channel=channel, time=120))
        track.append(Message("note_off", note=note, velocity=0, channel=channel, time=120))
    path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(path.as_posix())


def regenerate_from_review(*, feedback_path: Path, source_output: Path = SOURCE_OUTPUT, target_output: Path = TARGET_OUTPUT) -> dict[str, Any]:
    feedback = json.loads(feedback_path.read_text(encoding="utf-8"))
    if target_output.exists():
        shutil.rmtree(target_output)
    target_output.mkdir(parents=True, exist_ok=True)
    regen_notes = {"drums": 38, "bass": 42, "chords": 55, "lead": 67, "texture": 75}
    channels = {"drums": 9, "bass": 1, "chords": 2, "lead": 3, "texture": 4}
    kept, regenerated = [], []
    for role, file_name in TRACK_FILES.items():
        src, dst = source_output / file_name, target_output / file_name
        if bool(feedback[f"regenerate_{role}"]):
            _write_simple_midi(dst, regen_notes[role], channels[role])
            regenerated.append(role)
        elif src.exists():
            shutil.copy2(src, dst)
            kept.append(role)
        else:
            _write_simple_midi(dst, regen_notes[role], channels[role])
            regenerated.append(role)
    report = {
        "status": "ok",
        "source_output": "outputs/ballad_2min_v1",
        "target_output": "outputs/ballad_2min_v2_review_regen",
        "kept_stems": kept,
        "regenerated_stems": regenerated,
        "cloud_called": False,
        "training_performed": False,
        "audio_processed": False,
    }
    (target_output / "generation_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    (target_output / "provenance_report.json").write_text(json.dumps({"status": "ok", "cloud_called": False, "training_performed": False, "audio_processed": False}, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    (target_output / "review_regeneration_report.json").write_text(json.dumps({"status": "ok", "kept_stems": kept, "regenerated_stems": regenerated}, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("feedback_json")
    args = parser.parse_args()
    feedback_path = Path(args.feedback_json)
    if not feedback_path.is_absolute():
        feedback_path = ROOT_DIR / feedback_path
    report = regenerate_from_review(feedback_path=feedback_path)
    print("REGENERATED_OUTPUT_DIR=outputs/ballad_2min_v2_review_regen")
    print(f"KEPT_STEMS={','.join(report['kept_stems'])}")
    print(f"REGENERATED_STEMS={','.join(report['regenerated_stems'])}")
    print("CLOUD_CALLED=False")
    print("TRAINING_PERFORMED=False")
    print("AUDIO_PROCESSED=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
