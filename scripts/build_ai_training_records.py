from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

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
    )
except ModuleNotFoundError:  # pragma: no cover
    from feature_dataset_common import (  # type: ignore
        default_feature_dir,
        get_active_paths,
        load_json,
        now_iso,
        performance_metadata,
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
    rhythm_motifs_payload = rhythm_payload.get("rhythm_motifs", {})
    rhythm_motifs = rhythm_motifs_payload.get("motifs", []) if isinstance(rhythm_motifs_payload, dict) else []
    if not isinstance(rhythm_motifs, list):
        rhythm_motifs = []
    rhythm_motif_groups = rhythm_payload.get("rhythm_motif_groups", [])
    if not isinstance(rhythm_motif_groups, list):
        rhythm_motif_groups = []
    rhythm_pattern_index = rhythm_payload.get("rhythm_pattern_index", {})
    if not isinstance(rhythm_pattern_index, dict):
        rhythm_pattern_index = {}
    chord_summary = harmony_payload.get("chord_movement_summary", {})
    active_motion_regions = chord_summary.get("active_harmonic_motion_regions", []) if isinstance(chord_summary, dict) else []
    if not isinstance(active_motion_regions, list):
        active_motion_regions = []
    vamp_regions = chord_summary.get("repeated_chord_vamp_candidates", []) if isinstance(chord_summary, dict) else []
    if not isinstance(vamp_regions, list):
        vamp_regions = []
    harmony_pattern_index = harmony_payload.get("harmony_pattern_index", {})
    if not isinstance(harmony_pattern_index, dict):
        harmony_pattern_index = {}

    harmony_by_window: dict[str | None, list[dict[str, object]]] = {}
    if isinstance(harmony_records, list):
        for record in harmony_records:
            if isinstance(record, dict):
                harmony_by_window.setdefault(str(record.get("window_id")), []).append(record)

    tags_by_window: dict[str | None, list[dict[str, object]]] = {}
    if isinstance(tag_records, list):
        for record in tag_records:
            if not isinstance(record, dict):
                continue
            key = str(record.get("window_id"))
            tags_by_window.setdefault(key, []).append(record)

    output_records: list[dict[str, object]] = []

    def _top_tags_for(
        *,
        key: str,
        granularity: str,
        start_seconds: float | None,
        end_seconds: float | None,
    ) -> list[dict[str, object]]:
        local = []
        for tag in tags_by_window.get(key, []):
            if not isinstance(tag, dict):
                continue
            if granularity and str(tag.get("granularity", "")) != granularity:
                continue
            tag_start = tag.get("start_seconds")
            tag_end = tag.get("end_seconds")
            if (
                start_seconds is not None
                and end_seconds is not None
                and tag_start is not None
                and tag_end is not None
            ):
                try:
                    if float(tag_end) < float(start_seconds) or float(tag_start) > float(end_seconds):
                        continue
                except Exception:  # noqa: BLE001
                    pass
            local.append(
                {
                    "tag": str(tag.get("tag", "")),
                    "confidence": float(tag.get("confidence", 0.0) or 0.0),
                }
            )
        return sorted(local, key=lambda item: item["confidence"], reverse=True)[:5]
    if isinstance(rhythm_records, list):
        for rhythm_record in rhythm_records:
            if not isinstance(rhythm_record, dict):
                continue
            window_id_value = rhythm_record.get("window_id")
            key = str(window_id_value)
            granularity = str(rhythm_record.get("granularity", "window"))
            start_seconds = (
                float(rhythm_record.get("start_seconds", 0.0))
                if rhythm_record.get("start_seconds") is not None
                else None
            )
            end_seconds = (
                float(rhythm_record.get("end_seconds", 0.0))
                if rhythm_record.get("end_seconds") is not None
                else None
            )
            harmony_candidates = harmony_by_window.get(key, [])
            harmony_record = next(
                (
                    item
                    for item in harmony_candidates
                    if str(item.get("granularity", "window")) == granularity
                ),
                harmony_candidates[0] if harmony_candidates else {},
            )
            top_tags = _top_tags_for(
                key=key,
                granularity=granularity,
                start_seconds=start_seconds,
                end_seconds=end_seconds,
            )

            rhythm_features = rhythm_record.get("features", {}) if isinstance(rhythm_record.get("features"), dict) else {}
            harmony_features = (
                harmony_record.get("features", {})
                if isinstance(harmony_record, dict) and isinstance(harmony_record.get("features"), dict)
                else {}
            )
            input_features = {
                "rhythm_excerpt": {
                    "estimated_bpm": rhythm_features.get("estimated_bpm"),
                    "note_density_per_second": rhythm_features.get("note_density_per_second"),
                    "note_on_count": rhythm_features.get("note_on_count"),
                },
                "harmony_excerpt": {
                    "estimated_key": harmony_features.get("estimated_key"),
                    "estimated_mode": harmony_features.get("estimated_mode"),
                    "triad_match_score": harmony_features.get("triad_match_score"),
                },
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
                start_seconds=start_seconds,
                end_seconds=end_seconds,
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
            record["record_id"] = f"{performance_id}:{segment_run_id}:{record.get('window_id') or 'global'}:{len(output_records):04d}"
            record["granularity"] = granularity
            record["text_summary"] = (
                f"window={record.get('window_id')} bpm={input_features['rhythm_excerpt'].get('estimated_bpm')} "
                f"key={input_features['harmony_excerpt'].get('estimated_key')} "
                f"tags={[item['tag'] for item in top_tags]}"
            )
            record["feature_refs"] = {
                "rhythm_features_path": rhythm_path.resolve().as_posix(),
                "harmony_features_path": harmony_path.resolve().as_posix(),
                "tags_path": tags_path.resolve().as_posix(),
            }
            if granularity == "rhythm_region":
                record["motif_refs"] = [
                    str(item.get("motif_id"))
                    for item in rhythm_motifs
                    if isinstance(item, dict) and str(item.get("region_id")) == str(rhythm_record.get("region_id"))
                ]
                record["motif_group_refs"] = [
                    str(item.get("motif_group_id"))
                    for item in rhythm_motif_groups
                    if isinstance(item, dict) and str(rhythm_record.get("region_id")) in [str(x) for x in item.get("region_ids", [])]
                ][:10]
                family_matches = [
                    item
                    for item in rhythm_motif_groups
                    if isinstance(item, dict)
                    and str(rhythm_record.get("region_id")) in [str(x) for x in item.get("region_ids", [])]
                    and item.get("best_rhythm_family_match") not in {None, "", "unknown"}
                ]
                record["rhythm_family_match_refs"] = [
                    {
                        "motif_group_id": str(item.get("motif_group_id")),
                        "matched_family": item.get("best_rhythm_family_match"),
                        "confidence": item.get("rhythm_family_confidence"),
                    }
                    for item in family_matches[:8]
                ]
                if family_matches:
                    record["best_rhythm_family_match"] = family_matches[0].get("best_rhythm_family_match")
                else:
                    record["best_rhythm_family_match"] = "unknown"
                record["unknown_pattern"] = bool(record.get("motif_group_refs")) and not bool(family_matches)
                pattern = str(rhythm_features.get("token_pattern", ""))
                record["token_pattern_compact"] = pattern[:48] if len(pattern) <= 48 else pattern[:48] + "..."
            if granularity in {"window", "segment"}:
                start = start_seconds if start_seconds is not None else 0.0
                end = end_seconds if end_seconds is not None else start
                record["motif_count"] = sum(
                    1
                    for item in rhythm_motifs
                    if isinstance(item, dict)
                    and item.get("start_seconds") is not None
                    and item.get("end_seconds") is not None
                    and float(item.get("end_seconds", 0.0)) >= float(start)
                    and float(item.get("start_seconds", 0.0)) <= float(end)
                )
                record["chord_movement_count"] = sum(
                    1
                    for item in active_motion_regions
                    if isinstance(item, dict)
                    and item.get("start_seconds") is not None
                    and item.get("end_seconds") is not None
                    and float(item.get("end_seconds", 0.0)) >= float(start)
                    and float(item.get("start_seconds", 0.0)) <= float(end)
                )
                record["rhythm_concepts_summary"] = rhythm_pattern_index.get("concept_counts", {})
                record["rhythm_philosophy_summary"] = rhythm_pattern_index.get("philosophy_source_counts", {})
                record["rhythm_family_match_refs"] = rhythm_pattern_index.get("top_rhythm_family_matches", [])[:8]
                record["best_rhythm_family_match"] = (
                    rhythm_pattern_index.get("top_rhythm_family_matches", [{}])[0].get("matched_family")
                    if isinstance(rhythm_pattern_index.get("top_rhythm_family_matches"), list) and rhythm_pattern_index.get("top_rhythm_family_matches")
                    else "unknown"
                )
                unknown_list = rhythm_pattern_index.get("unknown_high_information_patterns", [])
                record["unknown_pattern"] = bool(unknown_list) if isinstance(unknown_list, list) else False
            output_records.append(record)

    # Add chord-region specific records from harmony output.
    if isinstance(harmony_records, list):
        for harmony_record in harmony_records:
            if not isinstance(harmony_record, dict):
                continue
            if str(harmony_record.get("granularity", "")) != "chord_region":
                continue
            key = str(harmony_record.get("window_id"))
            start_seconds = (
                float(harmony_record.get("start_seconds", 0.0))
                if harmony_record.get("start_seconds") is not None
                else None
            )
            end_seconds = (
                float(harmony_record.get("end_seconds", 0.0))
                if harmony_record.get("end_seconds") is not None
                else None
            )
            top_tags = _top_tags_for(
                key=key,
                granularity="chord_region",
                start_seconds=start_seconds,
                end_seconds=end_seconds,
            )
            harmony_features = harmony_record.get("features", {}) if isinstance(harmony_record.get("features"), dict) else {}
            record = ai_training_record(
                performance_id=performance_id,
                source_name=source_name,
                segment_run_id=segment_run_id,
                window_id=str(harmony_record.get("window_id")) if harmony_record.get("window_id") is not None else None,
                start_seconds=start_seconds,
                end_seconds=end_seconds,
                duration_seconds=(
                    float(harmony_record.get("duration_seconds", 0.0))
                    if harmony_record.get("duration_seconds") is not None
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
                confidence=float(harmony_record.get("confidence", 0.0) or 0.0),
                limitations=[str(item) for item in harmony_record.get("limitations", [])] if isinstance(harmony_record.get("limitations"), list) else [],
                label="feature_ready",
                input_features={
                    "harmony_excerpt": {
                        "estimated_key_candidates": harmony_features.get("estimated_key_candidates"),
                        "chord_change_count": harmony_features.get("chord_change_count"),
                        "root_motion_intervals": harmony_features.get("root_motion_intervals"),
                    },
                    "top_tags": top_tags,
                },
            )
            record["record_id"] = f"{performance_id}:{segment_run_id}:chord_region:{len(output_records):04d}"
            record["granularity"] = "chord_region"
            record["text_summary"] = (
                f"chord_region start={start_seconds} end={end_seconds} "
                f"changes={harmony_features.get('chord_change_count')} "
                f"tags={[item['tag'] for item in top_tags]}"
            )
            record["feature_refs"] = {
                "rhythm_features_path": rhythm_path.resolve().as_posix(),
                "harmony_features_path": harmony_path.resolve().as_posix(),
                "tags_path": tags_path.resolve().as_posix(),
            }
            record["chord_movement_refs"] = [
                str(item.get("region_id"))
                for item in active_motion_regions
                if isinstance(item, dict) and str(item.get("region_id")) == str(harmony_record.get("region_id"))
            ]
            record["harmony_pattern_index_refs"] = [
                str(item.get("sequence"))
                for item in harmony_pattern_index.get("repeated_chord_sequence_candidates", [])
                if isinstance(item, dict)
            ][:8]
            record["vamp_refs"] = [
                str(item.get("region_id"))
                for item in vamp_regions
                if isinstance(item, dict) and str(item.get("region_id")) == str(harmony_record.get("region_id"))
            ]
            output_records.append(record)

    output_path = target_dir / "ai_training_records.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(record, ensure_ascii=True) for record in output_records]
    output_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
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
