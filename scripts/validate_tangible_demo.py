from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from mido import MidiFile

REQUIRED_MIDI = [
    "generated_song.mid",
    "generated_drums.mid",
    "generated_bass.mid",
    "generated_chords.mid",
    "generated_lead.mid",
    "generated_texture_motifs.mid",
]
REQUIRED_REPORTS = [
    "demo_composition_plan.json",
    "demo_composition_plan.md",
    "generation_report.json",
    "generation_report.md",
    "ableton_track_plan.json",
    "ableton_track_plan.md",
]
AUDIO_EXTENSIONS = {".wav", ".aif", ".aiff", ".flac", ".mp3", ".ogg", ".m4a"}


def _count_note_on(path: Path) -> int:
    midi = MidiFile(str(path))
    total = 0
    for track in midi.tracks:
        for msg in track:
            if msg.type == "note_on" and int(getattr(msg, "velocity", 0)) > 0:
                total += 1
    return total


def validate_tangible_demo(output_dir: Path) -> dict[str, Any]:
    errors: list[str] = []
    note_counts: dict[str, int] = {}

    for file_name in REQUIRED_MIDI:
        path = output_dir / file_name
        if not path.exists():
            errors.append(f"Missing MIDI file: {path.as_posix()}")
            continue
        count = _count_note_on(path)
        note_counts[file_name] = count
        if count <= 0:
            errors.append(f"MIDI has no note_on events: {path.as_posix()}")

    for file_name in REQUIRED_REPORTS:
        path = output_dir / file_name
        if not path.exists():
            errors.append(f"Missing report file: {path.as_posix()}")

    report_path = output_dir / "generation_report.json"
    report_payload: dict[str, Any] = {}
    if report_path.exists():
        try:
            parsed = json.loads(report_path.read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                report_payload = parsed
        except Exception:  # noqa: BLE001
            errors.append("Invalid generation_report.json JSON")
    required_flags = [
        "prototype_generated_from_existing_examples",
        "not_model_trained",
        "not_ground_truth",
        "not_final_mix",
        "needs_human_review",
    ]
    for flag in required_flags:
        if report_payload.get(flag) is not True:
            errors.append(f"Missing/false provenance flag: {flag}")
    if report_payload.get("model_training_claim") is True:
        errors.append("Report incorrectly claims model training happened")
    if report_payload.get("synplant_automation_claim") is True:
        errors.append("Report incorrectly claims Synplant automation happened")

    copied_audio = [path.as_posix() for path in output_dir.rglob("*") if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS]
    if copied_audio:
        errors.append(f"Audio files copied to output folder: {len(copied_audio)}")

    suggestions_json = output_dir / "synplant_seed_suggestions.json"
    if suggestions_json.exists():
        try:
            parsed = json.loads(suggestions_json.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            errors.append("Invalid synplant_seed_suggestions.json JSON")
            parsed = []
        if not isinstance(parsed, list):
            errors.append("synplant_seed_suggestions.json must be a list")
            parsed = []
        required_fields = {
            "track_role",
            "requested_texture",
            "sample_id",
            "source_path",
            "asset_type_guess",
            "reason",
            "training_allowed_assumption",
            "requires_human_review",
            "note",
        }
        for idx, item in enumerate(parsed):
            if not isinstance(item, dict):
                errors.append(f"Suggestion entry {idx} is not a dict")
                continue
            missing = sorted(required_fields.difference(item.keys()))
            if missing:
                errors.append(f"Suggestion entry {idx} missing fields: {', '.join(missing)}")

    if errors:
        raise ValueError("\n".join(errors))

    return {"status": "ok", "output_dir": output_dir.as_posix(), "note_counts": note_counts}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate tangible generation demo outputs.")
    parser.add_argument(
        "output_dir",
        nargs="?",
        default="outputs/tangible_generation_v1",
        help="Output folder to validate (default: outputs/tangible_generation_v1)",
    )
    args = parser.parse_args()
    result = validate_tangible_demo(Path(args.output_dir))
    print(f"TANGIBLE_DEMO_VALIDATION_STATUS={result['status']}")
    for file_name, count in sorted(result["note_counts"].items()):
        print(f"NOTE_COUNT_{file_name.replace('.', '_').upper()}={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
