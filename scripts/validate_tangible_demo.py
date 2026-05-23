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


def _note_on_count(path: Path) -> int:
    midi = MidiFile(str(path))
    count = 0
    for track in midi.tracks:
        for msg in track:
            if msg.type == "note_on" and int(getattr(msg, "velocity", 0)) > 0:
                count += 1
    return count


def validate_tangible_demo(output_dir: Path) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    errors: list[str] = []
    note_counts: dict[str, int] = {}
    for name in REQUIRED_MIDI:
        path = output_dir / name
        if not path.exists():
            errors.append(f"Missing MIDI: {path.as_posix()}")
            continue
        count = _note_on_count(path)
        note_counts[name] = count
        if count <= 0:
            errors.append(f"No note_on events in: {path.as_posix()}")

    report_path = output_dir / "generation_report.json"
    if not report_path.exists():
        errors.append(f"Missing report: {report_path.as_posix()}")
    else:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        for key in [
            "prototype_generated_from_existing_examples",
            "not_model_trained",
            "not_ground_truth",
            "not_final_mix",
            "needs_human_review",
        ]:
            if report.get(key) is not True:
                errors.append(f"Missing or false provenance flag: {key}")
        if report.get("model_training_claim") is True:
            errors.append("Report incorrectly claims model training.")
        if report.get("synplant_automation_claim") is True:
            errors.append("Report incorrectly claims Synplant automation.")

    if errors:
        raise ValueError("\n".join(errors))
    return {"status": "ok", "note_counts": note_counts}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate tangible demo outputs.")
    parser.add_argument("output_dir", nargs="?", default="outputs/tangible_generation_v1")
    args = parser.parse_args()
    result = validate_tangible_demo(Path(args.output_dir))
    print(f"TANGIBLE_DEMO_VALIDATION_STATUS={result['status']}")
    for name, count in sorted(result["note_counts"].items()):
        print(f"NOTE_COUNT_{name.replace('.', '_').upper()}={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
