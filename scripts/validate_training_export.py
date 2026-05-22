from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _load_jsonl(path: Path) -> tuple[list[dict[str, Any]], int]:
    records: list[dict[str, Any]] = []
    parse_errors = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except Exception:  # noqa: BLE001
            parse_errors += 1
            continue
        if isinstance(parsed, dict):
            records.append(parsed)
        else:
            parse_errors += 1
    return records, parse_errors


def validate_training_export(export_folder: Path) -> dict[str, Any]:
    required_split_files = [
        "accepted_records.jsonl",
        "weak_label_records.jsonl",
        "audio_midi_only_records.jsonl",
        "review_required_records.jsonl",
        "quarantined_records.jsonl",
    ]
    errors: list[str] = []
    records_by_split: dict[str, list[dict[str, Any]]] = {}
    parse_errors_by_split: dict[str, int] = {}

    weak_label_statuses = {"weak_label", "heuristic_estimate", "interpretive_weak_label", "model_prediction"}
    for name in required_split_files:
        path = export_folder / name
        if not path.exists():
            errors.append(f"missing split file: {name}")
            continue
        records, parse_errors = _load_jsonl(path)
        records_by_split[name] = records
        parse_errors_by_split[name] = parse_errors
        if parse_errors:
            errors.append(f"jsonl parse errors in {name}: {parse_errors}")
        for record in records:
            for field in ["source_record_id", "performance_id", "granularity", "start_seconds", "end_seconds"]:
                if field not in record:
                    errors.append(f"record missing {field} in {name}")
                    break
            if "export_record_id" not in record or "export_split" not in record:
                errors.append(f"record missing export metadata in {name}")
            if name == "accepted_records.jsonl":
                label_status = str(record.get("label_status", ""))
                if label_status not in {"raw_observation", "derived_observation", "human_verified_label"}:
                    errors.append("accepted record has non-observation label_status")
                forbidden_keys = {"label", "weak_fields", "review_reasons", "best_rhythm_family_match", "motif_group_refs"}
                for key in forbidden_keys:
                    if key in record:
                        errors.append(f"accepted record contains weak/experimental field: {key}")
            if name == "weak_label_records.jsonl":
                if "evidence_refs" not in record or "confidence" not in record:
                    errors.append("weak label record missing evidence/confidence")
                label_status = str(record.get("label_status", ""))
                if label_status not in weak_label_statuses and label_status != "human_verified_label":
                    errors.append("weak label record has invalid label_status")
            if name == "review_required_records.jsonl":
                reasons = record.get("review_reasons")
                if not isinstance(reasons, list) or not reasons:
                    errors.append("review_required record missing review_reasons")

    quarantined_ids = {str(record.get("source_record_id")) for record in records_by_split.get("quarantined_records.jsonl", [])}
    accepted_ids = {str(record.get("source_record_id")) for record in records_by_split.get("accepted_records.jsonl", [])}
    overlap = sorted(quarantined_ids.intersection(accepted_ids))
    if overlap:
        errors.append(f"quarantined IDs duplicated in accepted: {len(overlap)}")

    manifest_path = export_folder / "export_manifest.json"
    manifest = {}
    if not manifest_path.exists():
        errors.append("missing export_manifest.json")
    else:
        try:
            loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                manifest = loaded
            else:
                errors.append("export_manifest.json is not an object")
        except Exception:  # noqa: BLE001
            errors.append("export_manifest.json parse error")

    if manifest:
        expected_counts = manifest.get("counts_per_split", {})
        if isinstance(expected_counts, dict):
            for name in required_split_files:
                expected = int(expected_counts.get(name.replace(".jsonl", ""), expected_counts.get(name, -1)) or 0)
                actual = len(records_by_split.get(name, []))
                if expected >= 0 and expected != actual:
                    errors.append(f"split count mismatch for {name}: expected={expected} actual={actual}")
        summary_keys = {
            "accepted_observation_count": "accepted_records.jsonl",
            "weak_label_count": "weak_label_records.jsonl",
            "audio_midi_only_count": "audio_midi_only_records.jsonl",
            "review_required_count": "review_required_records.jsonl",
            "quarantined_count": "quarantined_records.jsonl",
        }
        for key, file_name in summary_keys.items():
            if key in manifest:
                expected = int(manifest.get(key, -1) or 0)
                actual = len(records_by_split.get(file_name, []))
                if expected != actual:
                    errors.append(f"manifest summary mismatch for {key}: expected={expected} actual={actual}")

    return {
        "status": "success" if not errors else "failed",
        "export_folder": export_folder.resolve().as_posix(),
        "errors": errors,
        "counts": {name: len(records_by_split.get(name, [])) for name in required_split_files},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate training dataset export splits.")
    parser.add_argument("export_folder", help="Path to exported training split folder")
    args = parser.parse_args()
    summary = validate_training_export(Path(args.export_folder))
    print("TRAINING_EXPORT_VALIDATION=" + json.dumps(summary, ensure_ascii=True))
    return 0 if summary.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
