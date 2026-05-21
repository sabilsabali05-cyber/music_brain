from __future__ import annotations

import argparse
from pathlib import Path

try:
    from features.schema import ai_training_record
except ModuleNotFoundError:  # pragma: no cover
    from schema import ai_training_record  # type: ignore

try:
    from scripts.feature_dataset_common import (
        default_feature_dir,
        get_active_paths,
        load_json,
        now_iso,
        performance_metadata,
        save_json,
    )
except ModuleNotFoundError:  # pragma: no cover
    from feature_dataset_common import (  # type: ignore
        default_feature_dir,
        get_active_paths,
        load_json,
        now_iso,
        performance_metadata,
        save_json,
    )


def build_ai_training_records(performance_manifest_path: Path, *, output_dir: Path | None = None) -> Path:
    performance_manifest = load_json(performance_manifest_path)
    segments_manifest_path, analysis_path, merged_midi_path = get_active_paths(performance_manifest)
    performance_id, source_name, segment_run_id = performance_metadata(performance_manifest, segments_manifest_path)
    target_dir = output_dir or default_feature_dir(performance_id, segment_run_id)
    rhythm_path = target_dir / "rhythm_features.json"
    harmony_path = target_dir / "harmony_features.json"
    tags_path = target_dir / "tags.json"
    if not rhythm_path.exists():
        raise FileNotFoundError(f"Missing rhythm features: {rhythm_path}")
    if not harmony_path.exists():
        raise FileNotFoundError(f"Missing harmony features: {harmony_path}")
    if not tags_path.exists():
        raise FileNotFoundError(f"Missing tags: {tags_path}")

    rhythm_payload = load_json(rhythm_path)
    harmony_payload = load_json(harmony_path)
    tags_payload = load_json(tags_path)
    rhythm_records = rhythm_payload.get("records", [])
    harmony_records = harmony_payload.get("records", [])
    tag_records = tags_payload.get("tags", [])

    harmony_by_window: dict[str | None, dict[str, object]] = {}
    if isinstance(harmony_records, list):
        for record in harmony_records:
            if isinstance(record, dict):
                harmony_by_window[str(record.get("window_id"))] = record

    tags_by_window: dict[str | None, list[dict[str, object]]] = {}
    if isinstance(tag_records, list):
        for record in tag_records:
            if not isinstance(record, dict):
                continue
            key = str(record.get("window_id"))
            tags_by_window.setdefault(key, []).append(record)

    output_records: list[dict[str, object]] = []
    if isinstance(rhythm_records, list):
        for rhythm_record in rhythm_records:
            if not isinstance(rhythm_record, dict):
                continue
            window_id_value = rhythm_record.get("window_id")
            key = str(window_id_value)
            harmony_record = harmony_by_window.get(key, {})
            tags_for_window = tags_by_window.get(key, [])
            top_tags = sorted(
                [
                    {
                        "tag": str(tag.get("tag", "")),
                        "confidence": float(tag.get("confidence", 0.0) or 0.0),
                    }
                    for tag in tags_for_window
                    if isinstance(tag, dict)
                ],
                key=lambda item: item["confidence"],
                reverse=True,
            )[:5]

            input_features = {
                "rhythm": rhythm_record.get("features", {}),
                "harmony": harmony_record.get("features", {}) if isinstance(harmony_record, dict) else {},
                "top_tags": top_tags,
            }
            label = "needs_review" if any(t["confidence"] < 0.45 for t in top_tags) else "feature_ready"
            confidence = float(rhythm_record.get("confidence", 0.0) or 0.0)
            if isinstance(harmony_record, dict):
                confidence = min(confidence, float(harmony_record.get("confidence", 0.0) or 0.0))
            limitations = list(rhythm_record.get("limitations", [])) if isinstance(rhythm_record.get("limitations"), list) else []
            if isinstance(harmony_record, dict) and isinstance(harmony_record.get("limitations"), list):
                limitations.extend(str(item) for item in harmony_record.get("limitations", []))

            record = ai_training_record(
                performance_id=performance_id,
                source_name=source_name,
                segment_run_id=segment_run_id,
                window_id=str(window_id_value) if window_id_value is not None else None,
                start_seconds=(
                    float(rhythm_record.get("start_seconds", 0.0))
                    if rhythm_record.get("start_seconds") is not None
                    else None
                ),
                end_seconds=(
                    float(rhythm_record.get("end_seconds", 0.0))
                    if rhythm_record.get("end_seconds") is not None
                    else None
                ),
                duration_seconds=(
                    float(rhythm_record.get("duration_seconds", 0.0))
                    if rhythm_record.get("duration_seconds") is not None
                    else None
                ),
                source_artifact_paths={
                    "performance_manifest_path": performance_manifest_path.resolve().as_posix(),
                    "analysis_path": analysis_path.resolve().as_posix() if analysis_path else None,
                    "segments_manifest_path": segments_manifest_path.resolve().as_posix(),
                    "merged_midi_path": merged_midi_path.resolve().as_posix() if merged_midi_path and merged_midi_path.exists() else None,
                    "rhythm_features_path": rhythm_path.resolve().as_posix(),
                    "harmony_features_path": harmony_path.resolve().as_posix(),
                    "tags_path": tags_path.resolve().as_posix(),
                },
                confidence=confidence,
                limitations=limitations,
                label=label,
                input_features=input_features,
            )
            output_records.append(record)

    output_payload = {
        "performance_id": performance_id,
        "source_name": source_name,
        "segment_run_id": segment_run_id,
        "feature_version": "ai_training_v1",
        "extractor_name": "ai_training_record_builder_v1",
        "created_at": now_iso(),
        "record_count": len(output_records),
        "records": output_records,
    }
    output_path = target_dir / "ai_training_records.json"
    save_json(output_path, output_payload)
    return output_path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Build AI training records from feature+tag outputs.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    parser.add_argument("--output-dir", default=None, help="Optional output folder for feature files")
    args = parser.parse_args()
    output_dir = Path(args.output_dir) if args.output_dir else None
    output_path = build_ai_training_records(Path(args.performance_manifest), output_dir=output_dir)
    print(f"AI_TRAINING_RECORDS_PATH={output_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
