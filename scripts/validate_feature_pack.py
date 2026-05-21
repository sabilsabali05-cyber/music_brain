from __future__ import annotations

import argparse
from pathlib import Path

try:
    from scripts.feature_dataset_common import (
        default_feature_dir,
        get_active_paths,
        load_json,
        performance_metadata,
    )
except ModuleNotFoundError:  # pragma: no cover
    from feature_dataset_common import (  # type: ignore
        default_feature_dir,
        get_active_paths,
        load_json,
        performance_metadata,
    )


def validate_feature_pack(performance_manifest_path: Path, *, output_dir: Path | None = None) -> dict[str, object]:
    performance_manifest = load_json(performance_manifest_path)
    segments_manifest_path, _, _ = get_active_paths(performance_manifest)
    performance_id, _, segment_run_id = performance_metadata(performance_manifest, segments_manifest_path)
    feature_dir = output_dir or default_feature_dir(performance_id, segment_run_id)

    required_files = {
        "feature_pack_manifest": feature_dir / "feature_pack_manifest.json",
        "rhythm_features": feature_dir / "rhythm_features.json",
        "harmony_features": feature_dir / "harmony_features.json",
        "tags": feature_dir / "tags.json",
        "ai_training_records": feature_dir / "ai_training_records.json",
    }
    missing = [name for name, path in required_files.items() if not path.exists()]
    if missing:
        return {
            "status": "failed",
            "performance_id": performance_id,
            "feature_pack_dir": feature_dir.resolve().as_posix(),
            "missing_files": missing,
        }

    rhythm = load_json(required_files["rhythm_features"])
    harmony = load_json(required_files["harmony_features"])
    tags = load_json(required_files["tags"])
    ai_records = load_json(required_files["ai_training_records"])

    rhythm_records = rhythm.get("records", [])
    harmony_records = harmony.get("records", [])
    tag_records = tags.get("tags", [])
    training_records = ai_records.get("records", [])

    warnings: list[str] = []
    if not isinstance(rhythm_records, list) or len(rhythm_records) == 0:
        warnings.append("rhythm records are empty")
    if not isinstance(harmony_records, list) or len(harmony_records) == 0:
        warnings.append("harmony records are empty")
    if not isinstance(tag_records, list):
        warnings.append("tags payload malformed")
    if not isinstance(training_records, list):
        warnings.append("ai training payload malformed")

    confidence_issues = 0
    for collection in [rhythm_records, harmony_records, tag_records, training_records]:
        if not isinstance(collection, list):
            continue
        for item in collection:
            if not isinstance(item, dict):
                continue
            if "confidence" not in item:
                continue
            try:
                value = float(item.get("confidence", 0.0) or 0.0)
            except Exception:  # noqa: BLE001
                confidence_issues += 1
                continue
            if value < 0.0 or value > 1.0:
                confidence_issues += 1
    if confidence_issues:
        warnings.append(f"confidence out of range entries: {confidence_issues}")

    status = "success" if not missing else "failed"
    return {
        "status": status,
        "performance_id": performance_id,
        "feature_pack_dir": feature_dir.resolve().as_posix(),
        "rhythm_record_count": len(rhythm_records) if isinstance(rhythm_records, list) else 0,
        "harmony_record_count": len(harmony_records) if isinstance(harmony_records, list) else 0,
        "tag_count": len(tag_records) if isinstance(tag_records, list) else 0,
        "ai_training_record_count": len(training_records) if isinstance(training_records, list) else 0,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate extracted feature pack outputs for one performance.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    parser.add_argument("--output-dir", default=None, help="Optional output folder for feature files")
    args = parser.parse_args()
    output_dir = Path(args.output_dir) if args.output_dir else None
    summary = validate_feature_pack(Path(args.performance_manifest), output_dir=output_dir)
    print(f"FEATURE_PACK_DIR={summary.get('feature_pack_dir')}")
    print(f"VALIDATION_STATUS={summary.get('status')}")
    print(f"RHYTHM_RECORD_COUNT={summary.get('rhythm_record_count')}")
    print(f"HARMONY_RECORD_COUNT={summary.get('harmony_record_count')}")
    print(f"TAG_COUNT={summary.get('tag_count')}")
    print(f"AI_TRAINING_RECORD_COUNT={summary.get('ai_training_record_count')}")
    for warning in summary.get("warnings", []):
        print(f"VALIDATION_WARNING={warning}")
    if summary.get("status") != "success":
        raise SystemExit("Feature pack validation failed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
