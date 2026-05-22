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
    from features.rhythm_ontology import annotate_tag_with_rhythm_concepts
except ModuleNotFoundError:  # pragma: no cover
    from rhythm_ontology import annotate_tag_with_rhythm_concepts  # type: ignore

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
    rhythm_pattern_index = rhythm_payload.get("rhythm_pattern_index", {})
    rhythm_motif_groups = rhythm_payload.get("rhythm_motif_groups", [])
    harmony_pattern_index = harmony_payload.get("harmony_pattern_index", {})
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
            note_density = float((rhythm_features or {}).get("note_on_density_per_second", 0.0) or 0.0)
            mode = str((harmony_features or {}).get("estimated_mode", "unknown"))
            triad_score = float((harmony_features or {}).get("triad_match_score", 0.0) or 0.0)
            granularity = str(rhythm_record.get("granularity", "window"))
            record_limitations = (
                [str(item) for item in rhythm_record.get("limitations", [])]
                if isinstance(rhythm_record.get("limitations"), list)
                else []
            )
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
                    limitations=record_limitations,
                    tag=tag_name,
                    evidence=evidence,
                )
                tag_entry["granularity"] = granularity
                tag_entry["source_features"] = {
                    "rhythm_record_granularity": granularity,
                    "rhythm_feature_keys": sorted((rhythm_features or {}).keys()) if isinstance(rhythm_features, dict) else [],
                    "harmony_feature_keys": sorted((harmony_features or {}).keys()) if isinstance(harmony_features, dict) else [],
                }
                annotate_tag_with_rhythm_concepts(tag_entry)
                tags.append(tag_entry)

            # Local region-level evidence tags
            if note_density >= 6.0:
                dense_tag = tag_record(
                    performance_id=performance_id,
                    source_name=source_name,
                    segment_run_id=segment_run_id,
                    window_id=str(window_id) if window_id is not None else None,
                    start_seconds=float(rhythm_record.get("start_seconds", 0.0) or 0.0),
                    end_seconds=float(rhythm_record.get("end_seconds", 0.0) or 0.0),
                    duration_seconds=float(rhythm_record.get("duration_seconds", 0.0) or 0.0),
                    source_artifact_paths={
                        "performance_manifest_path": performance_manifest_path.resolve().as_posix(),
                        "analysis_path": analysis_path.resolve().as_posix() if analysis_path else None,
                        "segments_manifest_path": segments_manifest_path.resolve().as_posix(),
                        "merged_midi_path": merged_midi_path.resolve().as_posix() if merged_midi_path and merged_midi_path.exists() else None,
                        "rhythm_features_path": rhythm_path.resolve().as_posix(),
                        "harmony_features_path": harmony_path.resolve().as_posix(),
                    },
                    confidence=min(0.95, note_density / 10.0),
                    limitations=record_limitations,
                    tag="dense_region",
                    evidence={"note_on_density_per_second": note_density},
                )
                dense_tag["granularity"] = granularity
                dense_tag["source_features"] = {"metric": "note_on_density_per_second"}
                annotate_tag_with_rhythm_concepts(dense_tag)
                tags.append(dense_tag)
            if note_density <= 1.0:
                sparse_tag = tag_record(
                    performance_id=performance_id,
                    source_name=source_name,
                    segment_run_id=segment_run_id,
                    window_id=str(window_id) if window_id is not None else None,
                    start_seconds=float(rhythm_record.get("start_seconds", 0.0) or 0.0),
                    end_seconds=float(rhythm_record.get("end_seconds", 0.0) or 0.0),
                    duration_seconds=float(rhythm_record.get("duration_seconds", 0.0) or 0.0),
                    source_artifact_paths={
                        "performance_manifest_path": performance_manifest_path.resolve().as_posix(),
                        "analysis_path": analysis_path.resolve().as_posix() if analysis_path else None,
                        "segments_manifest_path": segments_manifest_path.resolve().as_posix(),
                        "merged_midi_path": merged_midi_path.resolve().as_posix() if merged_midi_path and merged_midi_path.exists() else None,
                        "rhythm_features_path": rhythm_path.resolve().as_posix(),
                        "harmony_features_path": harmony_path.resolve().as_posix(),
                    },
                    confidence=min(0.9, max(0.2, 1.0 - note_density)),
                    limitations=record_limitations,
                    tag="sparse_region",
                    evidence={"note_on_density_per_second": note_density},
                )
                sparse_tag["granularity"] = granularity
                sparse_tag["source_features"] = {"metric": "note_on_density_per_second"}
                annotate_tag_with_rhythm_concepts(sparse_tag)
                tags.append(sparse_tag)

    # Harmony-driven local tags
    if isinstance(harmony_records, list):
        for harmony_record in harmony_records:
            if not isinstance(harmony_record, dict):
                continue
            harmony_features = harmony_record.get("features", {})
            if not isinstance(harmony_features, dict):
                continue
            granularity = str(harmony_record.get("granularity", "window"))
            start_seconds = float(harmony_record.get("start_seconds", 0.0) or 0.0)
            end_seconds = float(harmony_record.get("end_seconds", 0.0) or 0.0)
            limitations = (
                [str(item) for item in harmony_record.get("limitations", [])]
                if isinstance(harmony_record.get("limitations"), list)
                else []
            )
            repeated = float(harmony_features.get("repeated_chord_score", 0.0) or 0.0)
            if repeated >= 0.5:
                vamp_tag = tag_record(
                    performance_id=performance_id,
                    source_name=source_name,
                    segment_run_id=segment_run_id,
                    window_id=str(harmony_record.get("window_id")) if harmony_record.get("window_id") is not None else None,
                    start_seconds=start_seconds,
                    end_seconds=end_seconds,
                    duration_seconds=max(0.0, end_seconds - start_seconds),
                    source_artifact_paths={
                        "performance_manifest_path": performance_manifest_path.resolve().as_posix(),
                        "analysis_path": analysis_path.resolve().as_posix() if analysis_path else None,
                        "segments_manifest_path": segments_manifest_path.resolve().as_posix(),
                        "merged_midi_path": merged_midi_path.resolve().as_posix() if merged_midi_path and merged_midi_path.exists() else None,
                        "harmony_features_path": harmony_path.resolve().as_posix(),
                    },
                    confidence=min(0.95, repeated),
                    limitations=limitations,
                    tag="repeated_chord_vamp_candidate",
                    evidence={"repeated_chord_score": repeated},
                )
                vamp_tag["granularity"] = granularity
                vamp_tag["source_features"] = {"metric": "repeated_chord_score"}
                annotate_tag_with_rhythm_concepts(vamp_tag)
                tags.append(vamp_tag)

    if isinstance(rhythm_motif_groups, list):
        region_time_by_id: dict[str, tuple[float | None, float | None]] = {}
        if isinstance(rhythm_records, list):
            for record in rhythm_records:
                if not isinstance(record, dict):
                    continue
                region_id = record.get("region_id")
                if region_id:
                    region_time_by_id[str(region_id)] = (
                        float(record.get("start_seconds", 0.0)) if record.get("start_seconds") is not None else None,
                        float(record.get("end_seconds", 0.0)) if record.get("end_seconds") is not None else None,
                    )
        for group in rhythm_motif_groups[:20]:
            if not isinstance(group, dict):
                continue
            group_repeat = int(group.get("group_repeat_count", 0) or 0)
            if group_repeat < 2:
                continue
            pattern = str(group.get("representative_pattern", ""))
            group_id = str(group.get("motif_group_id", ""))
            family = str(group.get("best_rhythm_family_match", "unknown"))
            matched_pattern_id = None
            matches = group.get("rhythm_lexicon_matches", [])
            if isinstance(matches, list) and matches and isinstance(matches[0], dict):
                matched_pattern_id = matches[0].get("matched_pattern_id")
            region_ids = [str(item) for item in group.get("region_ids", []) if item]
            start_seconds = None
            end_seconds = None
            for region_id in region_ids:
                if region_id in region_time_by_id:
                    start_seconds, end_seconds = region_time_by_id[region_id]
                    break
            confidence = min(0.95, 0.35 + (group_repeat / 12.0))
            new_tag = tag_record(
                performance_id=performance_id,
                source_name=source_name,
                segment_run_id=segment_run_id,
                window_id=None,
                start_seconds=start_seconds,
                end_seconds=end_seconds,
                duration_seconds=None,
                source_artifact_paths={
                    "performance_manifest_path": performance_manifest_path.resolve().as_posix(),
                    "analysis_path": analysis_path.resolve().as_posix() if analysis_path else None,
                    "segments_manifest_path": segments_manifest_path.resolve().as_posix(),
                    "merged_midi_path": merged_midi_path.resolve().as_posix() if merged_midi_path and merged_midi_path.exists() else None,
                    "rhythm_features_path": rhythm_path.resolve().as_posix(),
                },
                confidence=confidence,
                limitations=["heuristic motif group tag from token/ratio pattern index."],
                tag="repeated_rhythm_motif",
                evidence={
                    "motif_group_id": group_id,
                    "representative_pattern": pattern,
                    "group_repeat_count": group_repeat,
                    "matched_pattern_id": matched_pattern_id,
                    "matched_family": family,
                },
            )
            new_tag["granularity"] = "performance"
            new_tag["motif_group_id"] = group_id
            new_tag["source_features"] = {"metric": "rhythm_motif_groups"}
            annotate_tag_with_rhythm_concepts(new_tag)
            tags.append(new_tag)
            if "X" in pattern:
                accent_tag = dict(new_tag)
                accent_tag["tag"] = "recurring_accent_pattern"
                annotate_tag_with_rhythm_concepts(accent_tag)
                tags.append(accent_tag)
            if pattern.count("x") + pattern.count("X") >= 5:
                burst_tag = dict(new_tag)
                burst_tag["tag"] = "dense_burst_pattern"
                annotate_tag_with_rhythm_concepts(burst_tag)
                tags.append(burst_tag)
            if family and family != "unknown" and float(group.get("rhythm_family_confidence", 0.0) or 0.0) >= 0.65:
                family_tag_name = {
                    "tresillo_3_3_2": "rhythm_family_tresillo_candidate",
                    "clave": "rhythm_family_clave_candidate",
                    "backbeat": "rhythm_family_backbeat_candidate",
                    "shuffle": "rhythm_family_shuffle_candidate",
                    "twelve_eight_gospel": "rhythm_family_twelve_eight_gospel_candidate",
                    "dembow_like": "rhythm_family_dembow_candidate",
                    "boom_bap_backbeat": "rhythm_family_boom_bap_candidate",
                    "trap_subdivision": "rhythm_family_trap_subdivision_candidate",
                    "generic_vamp_cycle": "rhythm_family_vamp_cycle_candidate",
                }.get(family)
                if family_tag_name:
                    family_tag = tag_record(
                        performance_id=performance_id,
                        source_name=source_name,
                        segment_run_id=segment_run_id,
                        window_id=None,
                        start_seconds=start_seconds,
                        end_seconds=end_seconds,
                        duration_seconds=None,
                        source_artifact_paths={"rhythm_features_path": rhythm_path.resolve().as_posix()},
                        confidence=min(0.95, float(group.get("rhythm_family_confidence", 0.0) or 0.0)),
                        limitations=["family classification is heuristic and candidate-level only."],
                        tag=family_tag_name,
                        evidence={
                            "motif_group_id": group_id,
                            "matched_pattern_id": matched_pattern_id,
                            "matched_family": family,
                            "similarity": matches[0].get("similarity_breakdown") if isinstance(matches, list) and matches and isinstance(matches[0], dict) else {},
                        },
                    )
                    family_tag["matched_pattern_id"] = matched_pattern_id
                    family_tag["matched_family"] = family
                    family_tag["motif_group_id"] = group_id
                    family_tag["granularity"] = "rhythm_region"
                    annotate_tag_with_rhythm_concepts(family_tag)
                    tags.append(family_tag)

    if isinstance(rhythm_pattern_index, dict):
        if int(rhythm_pattern_index.get("steady_pulse_regions", 0) or 0) > 0:
            steady_tag = tag_record(
                performance_id=performance_id,
                source_name=source_name,
                segment_run_id=segment_run_id,
                window_id=None,
                start_seconds=None,
                end_seconds=None,
                duration_seconds=None,
                source_artifact_paths={"rhythm_features_path": rhythm_path.resolve().as_posix()},
                confidence=0.72,
                limitations=[],
                tag="steady_grid_candidate",
                evidence={"steady_pulse_regions": rhythm_pattern_index.get("steady_pulse_regions")},
            )
            steady_tag["granularity"] = "performance"
            annotate_tag_with_rhythm_concepts(steady_tag)
            tags.append(steady_tag)
        if int(rhythm_pattern_index.get("irregular_regions", 0) or 0) > 0:
            irregular_tag = tag_record(
                performance_id=performance_id,
                source_name=source_name,
                segment_run_id=segment_run_id,
                window_id=None,
                start_seconds=None,
                end_seconds=None,
                duration_seconds=None,
                source_artifact_paths={"rhythm_features_path": rhythm_path.resolve().as_posix()},
                confidence=0.7,
                limitations=[],
                tag="irregular_groove_candidate",
                evidence={"irregular_regions": rhythm_pattern_index.get("irregular_regions")},
            )
            irregular_tag["granularity"] = "performance"
            annotate_tag_with_rhythm_concepts(irregular_tag)
            tags.append(irregular_tag)
        if int(rhythm_pattern_index.get("triplet_grid_candidates", 0) or 0) > 0:
            tag_obj = tag_record(
                performance_id=performance_id,
                source_name=source_name,
                segment_run_id=segment_run_id,
                window_id=None,
                start_seconds=None,
                end_seconds=None,
                duration_seconds=None,
                source_artifact_paths={"rhythm_features_path": rhythm_path.resolve().as_posix()},
                confidence=0.6,
                limitations=[],
                tag="triplet_grid_candidate",
                evidence={"triplet_grid_candidates": rhythm_pattern_index.get("triplet_grid_candidates")},
            )
            tag_obj["granularity"] = "performance"
            annotate_tag_with_rhythm_concepts(tag_obj)
            tags.append(tag_obj)
        if int(rhythm_pattern_index.get("straight_grid_candidates", 0) or 0) > 0:
            tag_obj = tag_record(
                performance_id=performance_id,
                source_name=source_name,
                segment_run_id=segment_run_id,
                window_id=None,
                start_seconds=None,
                end_seconds=None,
                duration_seconds=None,
                source_artifact_paths={"rhythm_features_path": rhythm_path.resolve().as_posix()},
                confidence=0.6,
                limitations=[],
                tag="straight_grid_candidate",
                evidence={"straight_grid_candidates": rhythm_pattern_index.get("straight_grid_candidates")},
            )
            tag_obj["granularity"] = "performance"
            annotate_tag_with_rhythm_concepts(tag_obj)
            tags.append(tag_obj)
        if isinstance(rhythm_pattern_index.get("sparse_call_response_candidates"), list) and rhythm_pattern_index.get("sparse_call_response_candidates"):
            tag_obj = tag_record(
                performance_id=performance_id,
                source_name=source_name,
                segment_run_id=segment_run_id,
                window_id=None,
                start_seconds=None,
                end_seconds=None,
                duration_seconds=None,
                source_artifact_paths={"rhythm_features_path": rhythm_path.resolve().as_posix()},
                confidence=0.62,
                limitations=[],
                tag="sparse_call_response_candidate",
                evidence={"candidate_count": len(rhythm_pattern_index.get("sparse_call_response_candidates", []))},
            )
            tag_obj["granularity"] = "performance"
            annotate_tag_with_rhythm_concepts(tag_obj)
            tags.append(tag_obj)
        top_matches = rhythm_pattern_index.get("top_rhythm_family_matches", [])
        if isinstance(top_matches, list):
            for item in top_matches[:20]:
                if not isinstance(item, dict):
                    continue
                family = str(item.get("matched_family", "unknown"))
                family_tag_name = {
                    "tresillo_3_3_2": "rhythm_family_tresillo_candidate",
                    "clave": "rhythm_family_clave_candidate",
                    "backbeat": "rhythm_family_backbeat_candidate",
                    "shuffle": "rhythm_family_shuffle_candidate",
                    "twelve_eight_gospel": "rhythm_family_twelve_eight_gospel_candidate",
                    "dembow_like": "rhythm_family_dembow_candidate",
                    "boom_bap_backbeat": "rhythm_family_boom_bap_candidate",
                    "trap_subdivision": "rhythm_family_trap_subdivision_candidate",
                    "generic_vamp_cycle": "rhythm_family_vamp_cycle_candidate",
                }.get(family)
                if not family_tag_name:
                    continue
                confidence = float(item.get("confidence", 0.0) or 0.0)
                if confidence < 0.6:
                    continue
                family_tag = tag_record(
                    performance_id=performance_id,
                    source_name=source_name,
                    segment_run_id=segment_run_id,
                    window_id=None,
                    start_seconds=None,
                    end_seconds=None,
                    duration_seconds=None,
                    source_artifact_paths={"rhythm_features_path": rhythm_path.resolve().as_posix()},
                    confidence=min(0.95, confidence),
                    limitations=["rhythm family classification from lexicon match is candidate-level."],
                    tag=family_tag_name,
                    evidence={
                        "motif_group_id": item.get("motif_group_id"),
                        "matched_pattern_id": item.get("matched_pattern_id"),
                        "matched_family": family,
                    },
                )
                family_tag["matched_pattern_id"] = item.get("matched_pattern_id")
                family_tag["matched_family"] = family
                family_tag["motif_group_id"] = item.get("motif_group_id")
                family_tag["granularity"] = "rhythm_region"
                annotate_tag_with_rhythm_concepts(family_tag)
                tags.append(family_tag)

    if isinstance(harmony_pattern_index, dict):
        loop_candidates = harmony_pattern_index.get("chord_loop_candidates", [])
        if isinstance(loop_candidates, list) and loop_candidates:
            for candidate in loop_candidates[:5]:
                if not isinstance(candidate, dict):
                    continue
                tag_obj = tag_record(
                    performance_id=performance_id,
                    source_name=source_name,
                    segment_run_id=segment_run_id,
                    window_id=None,
                    start_seconds=float(candidate.get("start_seconds", 0.0) or 0.0),
                    end_seconds=float(candidate.get("end_seconds", 0.0) or 0.0),
                    duration_seconds=None,
                    source_artifact_paths={"harmony_features_path": harmony_path.resolve().as_posix()},
                    confidence=min(0.95, float(candidate.get("confidence", 0.6) or 0.6)),
                    limitations=[],
                    tag="repeated_chord_vamp_candidate",
                    evidence={"region_id": candidate.get("region_id"), "source": "harmony_pattern_index"},
                )
                tag_obj["granularity"] = "chord_region"
                annotate_tag_with_rhythm_concepts(tag_obj)
                tags.append(tag_obj)

    tags.sort(key=lambda item: float(item.get("confidence", 0.0)), reverse=True)
    grouped_tags: dict[str, dict[str, object]] = {}
    for tag in tags:
        name = str(tag.get("tag", ""))
        confidence = float(tag.get("confidence", 0.0) or 0.0)
        group = grouped_tags.get(name)
        if group is None:
            grouped_tags[name] = {
                "tag": name,
                "count": 1,
                "confidence_max": confidence,
                "confidence_sum": confidence,
                "example_start_seconds": tag.get("start_seconds"),
                "example_end_seconds": tag.get("end_seconds"),
                "best_representative": tag,
            }
            continue
        group["count"] = int(group.get("count", 0)) + 1
        group["confidence_sum"] = float(group.get("confidence_sum", 0.0) or 0.0) + confidence
        if confidence >= float(group.get("confidence_max", 0.0) or 0.0):
            group["confidence_max"] = confidence
            group["best_representative"] = tag

    grouped_list = []
    for name, group in grouped_tags.items():
        count = int(group.get("count", 0))
        grouped_list.append(
            {
                "tag": name,
                "count": count,
                "confidence_max": round(float(group.get("confidence_max", 0.0) or 0.0), 6),
                "confidence_mean": round((float(group.get("confidence_sum", 0.0) or 0.0) / max(1, count)), 6),
                "example_start_seconds": group.get("example_start_seconds"),
                "example_end_seconds": group.get("example_end_seconds"),
                "best_representative": group.get("best_representative"),
            }
        )
    grouped_list.sort(key=lambda item: (float(item.get("confidence_max", 0.0)), int(item.get("count", 0))), reverse=True)

    output_payload = {
        "performance_id": performance_id,
        "source_name": source_name,
        "segment_run_id": segment_run_id,
        "feature_version": "tagging_v1",
        "extractor_name": "feature_tagger_v1",
        "created_at": now_iso(),
        "tag_count": len(tags),
        "tag_counts": {item["tag"]: item["count"] for item in grouped_list},
        "grouped_tags": grouped_list,
        "top_unique_tags": grouped_list[:10],
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
