from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from features.schema import tag_record
except ModuleNotFoundError:  # pragma: no cover
    from schema import tag_record  # type: ignore

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


def _tag_candidates(
    *,
    estimated_bpm: float,
    note_density: float,
    mode: str,
    triad_score: float,
) -> list[tuple[str, float, dict[str, float]]]:
    tags: list[tuple[str, float, dict[str, float]]] = []
    if estimated_bpm > 140:
        tags.append(("fast_tempo", min(0.95, estimated_bpm / 220.0), {"estimated_bpm": estimated_bpm}))
    elif estimated_bpm > 0:
        tags.append(("slow_or_moderate_tempo", min(0.9, max(0.2, 1.0 - (estimated_bpm / 200.0))), {"estimated_bpm": estimated_bpm}))

    if note_density > 4.0:
        tags.append(("dense_activity", min(0.95, note_density / 10.0), {"note_density_per_second": note_density}))
    elif note_density > 0:
        tags.append(("sparse_activity", min(0.9, max(0.2, 1.0 - (note_density / 8.0))), {"note_density_per_second": note_density}))

    if mode in {"major", "minor"}:
        tags.append((f"{mode}_leaning_harmony", min(0.9, 0.3 + triad_score), {"triad_match_score": triad_score}))

    if triad_score < 0.18:
        tags.append(("ambiguous_harmony", min(0.95, 0.4 + (0.2 - triad_score)), {"triad_match_score": triad_score}))
    return tags


def tag_performance_features(performance_manifest_path: Path, *, output_dir: Path | None = None) -> Path:
    performance_manifest = load_json(performance_manifest_path)
    segments_manifest_path, analysis_path, merged_midi_path = get_active_paths(performance_manifest)
    performance_id, source_name, segment_run_id = performance_metadata(performance_manifest, segments_manifest_path)
    target_dir = output_dir or default_feature_dir(performance_id, segment_run_id)
    rhythm_path = target_dir / "rhythm_features.json"
    harmony_path = target_dir / "harmony_features.json"
    if not rhythm_path.exists():
        raise FileNotFoundError(f"Missing rhythm features: {rhythm_path}")
    if not harmony_path.exists():
        raise FileNotFoundError(f"Missing harmony features: {harmony_path}")
    rhythm_payload = load_json(rhythm_path)
    harmony_payload = load_json(harmony_path)

    rhythm_records = rhythm_payload.get("records", [])
    harmony_records = harmony_payload.get("records", [])
    harmony_by_window: dict[str | None, dict[str, object]] = {}
    if isinstance(harmony_records, list):
        for record in harmony_records:
            if isinstance(record, dict):
                harmony_by_window[str(record.get("window_id"))] = record

    tags: list[dict[str, object]] = []
    if isinstance(rhythm_records, list):
        for rhythm_record in rhythm_records:
            if not isinstance(rhythm_record, dict):
                continue
            window_id = rhythm_record.get("window_id")
            rhythm_features = rhythm_record.get("features", {})
            harmony_record = harmony_by_window.get(str(window_id))
            harmony_features = harmony_record.get("features", {}) if isinstance(harmony_record, dict) else {}
            estimated_bpm = float((rhythm_features or {}).get("estimated_bpm", 0.0) or 0.0)
            note_density = float((rhythm_features or {}).get("note_density_per_second", 0.0) or 0.0)
            mode = str((harmony_features or {}).get("estimated_mode", "unknown"))
            triad_score = float((harmony_features or {}).get("triad_match_score", 0.0) or 0.0)
            for tag_name, confidence, evidence in _tag_candidates(
                estimated_bpm=estimated_bpm,
                note_density=note_density,
                mode=mode,
                triad_score=triad_score,
            ):
                tag_entry = tag_record(
                    performance_id=performance_id,
                    source_name=source_name,
                    segment_run_id=segment_run_id,
                    window_id=str(window_id) if window_id is not None else None,
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
                    },
                    confidence=confidence,
                    limitations=[],
                    tag=tag_name,
                    evidence=evidence,
                )
                tags.append(tag_entry)

    tags.sort(key=lambda item: float(item.get("confidence", 0.0)), reverse=True)
    output_payload = {
        "performance_id": performance_id,
        "source_name": source_name,
        "segment_run_id": segment_run_id,
        "feature_version": "tagging_v1",
        "extractor_name": "feature_tagger_v1",
        "created_at": now_iso(),
        "tag_count": len(tags),
        "tags": tags,
    }
    output_path = target_dir / "tags.json"
    save_json(output_path, output_payload)
    return output_path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate performance tags from rhythm+harmony feature outputs.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    parser.add_argument("--output-dir", default=None, help="Optional output folder for feature files")
    args = parser.parse_args()
    output_dir = Path(args.output_dir) if args.output_dir else None
    output_path = tag_performance_features(Path(args.performance_manifest), output_dir=output_dir)
    print(f"TAGS_PATH={output_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
