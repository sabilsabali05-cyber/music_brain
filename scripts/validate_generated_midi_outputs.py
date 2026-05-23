from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from mido import MidiFile


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:  # noqa: BLE001
        return fallback


def validate_generated_midi_outputs(output_folder: Path) -> dict[str, Any]:
    folder = output_folder.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    report_path = folder / "generation_report.json"
    summary_path = folder / "generation_summary.md"

    if not report_path.exists():
        errors.append("generation_report.json is missing")
        return {"status": "failed", "output_folder": folder.as_posix(), "errors": errors, "warnings": warnings}
    if not summary_path.exists():
        warnings.append("generation_summary.md is missing")

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"generation_report.json is invalid JSON: {exc}")
        return {"status": "failed", "output_folder": folder.as_posix(), "errors": errors, "warnings": warnings}

    provenance_notice = report.get("provenance_notice", {})
    if not isinstance(provenance_notice, dict):
        provenance_notice = {}
    if provenance_notice.get("prototype_generated_from_existing_examples") is not True:
        errors.append("provenance_notice.prototype_generated_from_existing_examples must be true")
    if provenance_notice.get("not_original_model_composition") is not True:
        errors.append("provenance_notice.not_original_model_composition must be true")
    if provenance_notice.get("not_ground_truth") is not True:
        errors.append("provenance_notice.not_ground_truth must be true")
    if provenance_notice.get("model_trained_output") is not False:
        errors.append("provenance_notice.model_trained_output must be false")

    generated_examples = report.get("generated_examples", [])
    if not isinstance(generated_examples, list):
        generated_examples = []
    if not generated_examples:
        errors.append("generated_examples is empty")

    validated_midi_files = 0
    for idx, row in enumerate(generated_examples):
        if not isinstance(row, dict):
            errors.append(f"generated_examples[{idx}] is not an object")
            continue

        for required in ("example_id", "task_type", "split_recommendation", "quality_score", "output_midi_path"):
            if required not in row:
                errors.append(f"generated_examples[{idx}] missing required field: {required}")
        if not str(row.get("example_id", "")).strip():
            errors.append(f"generated_examples[{idx}] missing source example_id")
        if str(row.get("quality_score", "")).strip() == "":
            errors.append(f"generated_examples[{idx}] missing quality_score")
        if _safe_float(row.get("quality_score"), -1.0) < 0:
            errors.append(f"generated_examples[{idx}] quality_score is invalid")

        provenance = row.get("provenance", {})
        if not isinstance(provenance, dict):
            provenance = {}
        if provenance.get("prototype_generated_from_existing_examples") is not True:
            errors.append(f"generated_examples[{idx}] provenance prototype flag missing")
        if provenance.get("not_ground_truth") is not True:
            errors.append(f"generated_examples[{idx}] provenance not_ground_truth must be true")
        if provenance.get("model_trained_output") is not False:
            errors.append(f"generated_examples[{idx}] provenance model_trained_output must be false")
        if provenance.get("weak_labels_promoted_to_ground_truth") is not False:
            errors.append(f"generated_examples[{idx}] weak_labels_promoted_to_ground_truth must be false")

        midi_path = Path(str(row.get("output_midi_path", "")))
        if not midi_path.exists():
            errors.append(f"generated_examples[{idx}] MIDI file missing: {midi_path.as_posix()}")
            continue
        try:
            midi = MidiFile(str(midi_path))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"generated_examples[{idx}] MIDI parse failed: {exc}")
            continue
        note_on_count = sum(
            1
            for track in midi.tracks
            for message in track
            if getattr(message, "type", "") == "note_on" and int(getattr(message, "velocity", 0)) > 0
        )
        if note_on_count <= 0:
            errors.append(f"generated_examples[{idx}] MIDI has zero note_on events: {midi_path.as_posix()}")
            continue
        validated_midi_files += 1

    status = "success" if not errors else "failed"
    return {
        "status": status,
        "output_folder": folder.as_posix(),
        "generation_report_path": report_path.as_posix(),
        "validated_midi_files": validated_midi_files,
        "total_reported_examples": len(generated_examples),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate prototype generated MIDI outputs.")
    parser.add_argument("output_folder", help="Folder containing generated MIDI outputs and generation report")
    args = parser.parse_args()
    result = validate_generated_midi_outputs(Path(args.output_folder))
    print(json.dumps(result, indent=2, ensure_ascii=True))
    if result["status"] != "success":
        raise SystemExit(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
