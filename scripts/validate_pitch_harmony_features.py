from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.feature_dataset_common import default_feature_dir, get_active_paths, load_json, performance_metadata  # noqa: E402


def _validate_time_ranges(records: list[dict[str, Any]], errors: list[str], *, label: str) -> None:
    for idx, record in enumerate(records):
        try:
            start = float(record.get("start_seconds", 0.0))
            end = float(record.get("end_seconds", 0.0))
        except Exception:  # noqa: BLE001
            errors.append(f"{label}[{idx}] invalid time values")
            continue
        if end < start:
            errors.append(f"{label}[{idx}] end_seconds < start_seconds")


def validate_pitch_harmony_features(performance_manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(performance_manifest_path)
    segments_manifest_path, _, _ = get_active_paths(manifest)
    segments_manifest = load_json(segments_manifest_path)
    performance_id, _, segment_run_id = performance_metadata(manifest, segments_manifest_path)
    base_dir = default_feature_dir(performance_id, segment_run_id)
    pitch_dir = base_dir / "pitch_harmony"
    payload_path = pitch_dir / "pitch_harmony_features.json"
    errors: list[str] = []

    if not payload_path.exists():
        errors.append(f"missing pitch harmony payload: {payload_path.as_posix()}")
        return {"status": "failed", "errors": errors}

    payload = load_json(payload_path)
    key_sections = [
        "pitch_observations",
        "interval_analysis",
        "melody_contour",
        "harmony_sonority",
        "chord_movement",
        "counterpoint",
        "tuning_system",
    ]
    for section in key_sections:
        if not isinstance(payload.get(section), list):
            errors.append(f"missing or invalid section: {section}")

    interval_records = payload.get("interval_analysis", [])
    if isinstance(interval_records, list):
        for idx, record in enumerate(interval_records):
            if not isinstance(record, dict):
                errors.append(f"interval_analysis[{idx}] not object")
                continue
            if not isinstance(record.get("interval_class_histogram"), dict):
                errors.append(f"interval_analysis[{idx}] missing interval_class_histogram")

    sonority_records = payload.get("harmony_sonority", [])
    if isinstance(sonority_records, list):
        for idx, record in enumerate(sonority_records):
            if not isinstance(record, dict):
                errors.append(f"harmony_sonority[{idx}] not object")
                continue
            if "confidence" not in record:
                errors.append(f"harmony_sonority[{idx}] missing confidence")
            if not isinstance(record.get("limitations"), list):
                errors.append(f"harmony_sonority[{idx}] missing limitations")
            if record.get("hard_label") is True and float(record.get("confidence", 0.0) or 0.0) < 0.8:
                errors.append(f"harmony_sonority[{idx}] has hard label with low confidence")

    movement_records = payload.get("chord_movement", [])
    if isinstance(movement_records, list):
        for idx, record in enumerate(movement_records):
            if not isinstance(record.get("evidence"), dict):
                errors.append(f"chord_movement[{idx}] missing evidence")
            if not isinstance(record.get("limitations"), list):
                errors.append(f"chord_movement[{idx}] missing limitations")

    tuning_records = payload.get("tuning_system", [])
    if isinstance(tuning_records, list):
        for idx, record in enumerate(tuning_records):
            if "microtonal_analysis_available" not in record:
                errors.append(f"tuning_system[{idx}] missing microtonal_analysis_available")
            if str(record.get("microtonal_evidence_type", "")) not in {
                "pitch_bend",
                "non_12tet_audio_estimate",
                "repeated_detuned_pitch",
                "external_analyzer_required",
                "unavailable",
            }:
                errors.append(f"tuning_system[{idx}] invalid microtonal_evidence_type")

    macro = payload.get("macro_record", {})
    if isinstance(macro, dict):
        hypotheses = macro.get("key_hypotheses", [])
        if not isinstance(hypotheses, list):
            errors.append("macro_record.key_hypotheses missing")
        else:
            for idx, item in enumerate(hypotheses):
                if not isinstance(item, dict):
                    continue
                if str(item.get("label", "")).lower() in {"major", "minor", "ionian", "dorian", "c_major"} and float(item.get("confidence", 0.0) or 0.0) < 0.8:
                    errors.append(f"macro key_hypotheses[{idx}] appears hard-tonal without high confidence")

    for section in key_sections:
        records = payload.get(section, [])
        if isinstance(records, list):
            _validate_time_ranges([record for record in records if isinstance(record, dict)], errors, label=section)

    if payload.get("microtonal_analysis_available") is False and float(payload.get("microtonal_confidence", 0.0) or 0.0) > 0.5:
        errors.append("microtonal_confidence too high while microtonal_analysis_available is false")

    return {
        "status": "success" if not errors else "failed",
        "payload_path": payload_path.resolve().as_posix(),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate pitch/harmony/tuning intelligence outputs.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    args = parser.parse_args()
    summary = validate_pitch_harmony_features(Path(args.performance_manifest))
    print("PITCH_HARMONY_VALIDATION=" + json.dumps(summary, ensure_ascii=True))
    return 0 if summary.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
