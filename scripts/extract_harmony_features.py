from __future__ import annotations

import argparse
from pathlib import Path

try:
    from features.schema import harmony_feature_record, performance_feature_pack
except ModuleNotFoundError:  # pragma: no cover
    from schema import harmony_feature_record, performance_feature_pack  # type: ignore

try:
    from scripts.feature_dataset_common import (
        collect_midi_sources,
        default_feature_dir,
        get_active_paths,
        harmony_features_from_events,
        load_json,
        midi_note_events,
        now_iso,
        performance_metadata,
        save_json,
    )
except ModuleNotFoundError:  # pragma: no cover
    from feature_dataset_common import (  # type: ignore
        collect_midi_sources,
        default_feature_dir,
        get_active_paths,
        harmony_features_from_events,
        load_json,
        midi_note_events,
        now_iso,
        performance_metadata,
        save_json,
    )


def extract_harmony_features(performance_manifest_path: Path, *, output_dir: Path | None = None) -> Path:
    performance_manifest = load_json(performance_manifest_path)
    segments_manifest_path, analysis_path, merged_midi_path = get_active_paths(performance_manifest)
    if not segments_manifest_path.exists():
        raise FileNotFoundError(f"Active segments manifest missing: {segments_manifest_path}")
    segments_manifest = load_json(segments_manifest_path)

    performance_id, source_name, segment_run_id = performance_metadata(performance_manifest, segments_manifest_path)
    target_dir = output_dir or default_feature_dir(performance_id, segment_run_id)
    target_dir.mkdir(parents=True, exist_ok=True)

    midi_sources, source_limitations, source_mode = collect_midi_sources(
        segments_manifest=segments_manifest,
        merged_midi_path=merged_midi_path,
    )
    records: list[dict[str, object]] = []
    confidence_scores: list[float] = []
    limitations = list(source_limitations)

    for source in midi_sources:
        events = midi_note_events(source.path)
        feature_values = harmony_features_from_events(events)
        confidence = 0.88 if source.kind == "merged" else 0.68
        record_limitations: list[str] = []
        if source_mode == "window_fallback":
            record_limitations.append("window fallback used because merged MIDI was unavailable.")
        unique_pcs = int(feature_values.get("unique_pitch_classes", 0) or 0)
        note_count = int(feature_values.get("note_on_count", 0) or 0)
        if note_count < 10 or unique_pcs < 3:
            confidence = min(confidence, 0.42)
            record_limitations.append("limited harmonic evidence; inferred key/mode are low confidence.")
        source_paths = {
            "performance_manifest_path": performance_manifest_path.resolve().as_posix(),
            "analysis_path": analysis_path.resolve().as_posix() if analysis_path else None,
            "segments_manifest_path": segments_manifest_path.resolve().as_posix(),
            "merged_midi_path": merged_midi_path.resolve().as_posix() if merged_midi_path and merged_midi_path.exists() else None,
            "midi_source_path": source.path.resolve().as_posix(),
        }
        record = harmony_feature_record(
            performance_id=performance_id,
            source_name=source_name,
            segment_run_id=segment_run_id,
            window_id=source.window_id,
            start_seconds=source.start_seconds,
            end_seconds=source.end_seconds,
            duration_seconds=(
                (source.end_seconds - source.start_seconds)
                if (source.start_seconds is not None and source.end_seconds is not None)
                else None
            ),
            source_artifact_paths=source_paths,
            confidence=confidence,
            limitations=record_limitations,
            features=feature_values,
        )
        records.append(record)
        confidence_scores.append(confidence)

    if not records:
        limitations.append("no MIDI source records were generated.")
    pack_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
    summary = {
        "record_count": len(records),
        "source_mode": source_mode,
        "low_confidence_record_count": sum(1 for score in confidence_scores if score < 0.5),
    }
    payload = performance_feature_pack(
        performance_id=performance_id,
        source_name=source_name,
        segment_run_id=segment_run_id,
        source_artifact_paths={
            "performance_manifest_path": performance_manifest_path.resolve().as_posix(),
            "analysis_path": analysis_path.resolve().as_posix() if analysis_path else None,
            "segments_manifest_path": segments_manifest_path.resolve().as_posix(),
            "merged_midi_path": merged_midi_path.resolve().as_posix() if merged_midi_path and merged_midi_path.exists() else None,
        },
        feature_version="harmony_pack_v1",
        extractor_name="harmony_feature_extractor_v1",
        confidence=pack_confidence,
        limitations=limitations,
        summary=summary,
        records=records,
    )
    payload["generated_at"] = now_iso()
    output_path = target_dir / "harmony_features.json"
    save_json(output_path, payload)
    return output_path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract harmony features from active performance artifacts.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    parser.add_argument("--output-dir", default=None, help="Optional output folder for feature files")
    args = parser.parse_args()
    output_dir = Path(args.output_dir) if args.output_dir else None
    output_path = extract_harmony_features(Path(args.performance_manifest), output_dir=output_dir)
    print(f"HARMONY_FEATURES_PATH={output_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
