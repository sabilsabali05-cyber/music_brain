from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from features.schema import harmony_feature_record, performance_feature_pack
except ModuleNotFoundError:  # pragma: no cover
    from schema import harmony_feature_record, performance_feature_pack  # type: ignore

try:
    from scripts.feature_dataset_common import (
        build_time_bins,
        collect_global_events,
        default_feature_dir,
        get_active_paths,
        harmony_feature_vector,
        load_json,
        now_iso,
        performance_metadata,
        save_json,
        successful_windows_with_midi,
    )
except ModuleNotFoundError:  # pragma: no cover
    from feature_dataset_common import (  # type: ignore
        build_time_bins,
        collect_global_events,
        default_feature_dir,
        get_active_paths,
        harmony_feature_vector,
        load_json,
        now_iso,
        performance_metadata,
        save_json,
        successful_windows_with_midi,
    )


def extract_harmony_features(
    performance_manifest_path: Path,
    *,
    output_dir: Path | None = None,
    bin_seconds: float = 4.0,
) -> Path:
    performance_manifest = load_json(performance_manifest_path)
    segments_manifest_path, analysis_path, merged_midi_path = get_active_paths(performance_manifest)
    if not segments_manifest_path.exists():
        raise FileNotFoundError(f"Active segments manifest missing: {segments_manifest_path}")
    segments_manifest = load_json(segments_manifest_path)

    performance_id, source_name, segment_run_id = performance_metadata(performance_manifest, segments_manifest_path)
    target_dir = output_dir or default_feature_dir(performance_id, segment_run_id)
    target_dir.mkdir(parents=True, exist_ok=True)

    global_events, source_mode, source_limitations = collect_global_events(
        segments_manifest=segments_manifest,
        merged_midi_path=merged_midi_path,
    )
    windows = successful_windows_with_midi(segments_manifest)
    musical_segments = segments_manifest.get("musical_segments", [])
    duration_seconds = float(
        performance_manifest.get("duration_seconds")
        or segments_manifest.get("duration_seconds")
        or (global_events[-1][0] if global_events else 0.0)
    )
    records: list[dict[str, object]] = []
    confidence_scores: list[float] = []
    limitations = list(source_limitations)

    source_paths = {
        "performance_manifest_path": performance_manifest_path.resolve().as_posix(),
        "analysis_path": analysis_path.resolve().as_posix() if analysis_path else None,
        "segments_manifest_path": segments_manifest_path.resolve().as_posix(),
        "merged_midi_path": merged_midi_path.resolve().as_posix() if merged_midi_path and merged_midi_path.exists() else None,
    }

    def _append_record(
        *,
        granularity: str,
        start_seconds: float,
        end_seconds: float,
        analysis_bin_seconds: float | None = None,
        window_id: str | None = None,
        segment_id: str | None = None,
        region_id: str | None = None,
    ) -> None:
        feature_values = harmony_feature_vector(
            global_events,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            bin_seconds=analysis_bin_seconds if analysis_bin_seconds is not None else bin_seconds,
        )
        note_count = int(sum(feature_values.get("pitch_class_histogram", [])) if isinstance(feature_values.get("pitch_class_histogram"), list) else 0)
        confidence = 0.88 if source_mode == "merged" else 0.7
        confidence = min(confidence, 0.3 + min(0.58, note_count / 150.0))
        record_limitations: list[str] = []
        if source_mode == "window_fallback":
            record_limitations.append("window fallback used because merged MIDI was unavailable.")
        unique_pcs = sum(1 for value in (feature_values.get("pitch_class_histogram", []) or []) if value > 0)
        if note_count < 10 or unique_pcs < 3:
            confidence = min(confidence, 0.42)
            record_limitations.append("limited harmonic evidence; inferred key/mode are low confidence.")
        record = harmony_feature_record(
            performance_id=performance_id,
            source_name=source_name,
            segment_run_id=segment_run_id,
            window_id=window_id,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            duration_seconds=max(0.0, end_seconds - start_seconds),
            source_artifact_paths=source_paths,
            confidence=confidence,
            limitations=record_limitations,
            features=feature_values,
        )
        record["granularity"] = granularity
        if segment_id is not None:
            record["segment_id"] = segment_id
        if region_id is not None:
            record["region_id"] = region_id
        records.append(record)
        confidence_scores.append(confidence)

    _append_record(granularity="performance", start_seconds=0.0, end_seconds=duration_seconds)

    if isinstance(musical_segments, list):
        for segment in musical_segments:
            if not isinstance(segment, dict):
                continue
            start = float(segment.get("global_start_seconds", 0.0) or 0.0)
            end = float(segment.get("global_end_seconds", start) or start)
            _append_record(
                granularity="segment",
                segment_id=str(segment.get("segment_id", "")),
                start_seconds=start,
                end_seconds=end,
            )

    for window in windows:
        start = float(window.get("core_start_seconds", 0.0) or 0.0)
        end = float(window.get("core_end_seconds", start) or start)
        _append_record(
            granularity="window",
            window_id=str(window.get("window_id", "")),
            start_seconds=start,
            end_seconds=end,
        )

    for index, (bin_start, bin_end) in enumerate(build_time_bins(0.0, duration_seconds, bin_seconds=bin_seconds)):
        _append_record(
            granularity="chord_region",
            region_id=f"chord_region_{index:04d}",
            start_seconds=bin_start,
            end_seconds=bin_end,
            analysis_bin_seconds=max(1.0, bin_seconds / 2.0),
        )

    if not records:
        limitations.append("no MIDI source records were generated.")
    pack_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
    by_granularity: dict[str, int] = {}
    for record in records:
        key = str(record.get("granularity", "unknown"))
        by_granularity[key] = by_granularity.get(key, 0) + 1
    summary = {
        "record_count": len(records),
        "source_mode": source_mode,
        "low_confidence_record_count": sum(1 for score in confidence_scores if score < 0.5),
        "record_count_by_granularity": by_granularity,
        "bin_seconds": float(bin_seconds),
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
    parser.add_argument("--bin-seconds", type=float, default=4.0)
    args = parser.parse_args()
    output_dir = Path(args.output_dir) if args.output_dir else None
    output_path = extract_harmony_features(
        Path(args.performance_manifest),
        output_dir=output_dir,
        bin_seconds=args.bin_seconds,
    )
    print(f"HARMONY_FEATURES_PATH={output_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
