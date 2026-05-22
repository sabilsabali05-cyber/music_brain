from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from features.schema import performance_feature_pack, rhythm_feature_record
except ModuleNotFoundError:  # pragma: no cover
    from schema import performance_feature_pack, rhythm_feature_record  # type: ignore

try:
    from features.rhythm_ontology import annotate_feature_record_with_rhythm_concepts, concept_count, philosophy_count
except ModuleNotFoundError:  # pragma: no cover
    from rhythm_ontology import annotate_feature_record_with_rhythm_concepts, concept_count, philosophy_count  # type: ignore

try:
    from features.rhythm_lexicon import classify_rhythm_pattern
except ModuleNotFoundError:  # pragma: no cover
    from rhythm_lexicon import classify_rhythm_pattern  # type: ignore

try:
    from scripts.feature_dataset_common import (
        build_time_bins,
        collect_global_events,
        events_in_range,
        default_feature_dir,
        get_active_paths,
        load_json,
        now_iso,
        performance_metadata,
        rhythm_feature_vector,
        save_json,
        successful_windows_with_midi,
    )
except ModuleNotFoundError:  # pragma: no cover
    from feature_dataset_common import (  # type: ignore
        build_time_bins,
        collect_global_events,
        default_feature_dir,
        events_in_range,
        get_active_paths,
        load_json,
        now_iso,
        performance_metadata,
        rhythm_feature_vector,
        save_json,
        successful_windows_with_midi,
    )


def _tokenize_region(
    events: list[tuple[float, int, int]],
    *,
    start_seconds: float,
    end_seconds: float,
    pulse_seconds: float,
    note_count: int,
) -> dict[str, object]:
    local = events_in_range(events, start_seconds=start_seconds, end_seconds=end_seconds)
    duration = max(0.0, end_seconds - start_seconds)
    if not local or duration <= 0:
        return {
            "quantization_grid_seconds": 0.0,
            "quantization_confidence": 0.0,
            "token_pattern": "",
            "accent_pattern": "",
            "limitations": ["insufficient local events for quantization."],
            "onset_positions": [],
            "velocity_pattern": [],
            "ioi_seconds": [],
            "ratio_pattern": [],
        }
    grid = pulse_seconds / 2.0 if pulse_seconds > 0 else max(0.1, duration / 16.0)
    steps = max(8, min(64, int(round(duration / max(0.001, grid)))))
    grid = duration / steps if steps > 0 else duration
    velocities = [int(item[2]) for item in local]
    mean_velocity = sum(velocities) / max(1, len(velocities))
    accent_threshold = mean_velocity + 6.0
    tokens = ["."] * steps
    accents = ["."] * steps
    onset_positions: list[int] = []
    for time_value, _, velocity in local:
        rel = max(0.0, min(duration, time_value - start_seconds))
        step_idx = min(steps - 1, max(0, int(round(rel / max(1e-9, grid)))))
        tokens[step_idx] = "x"
        accents[step_idx] = "X" if velocity >= accent_threshold else "x"
        onset_positions.append(step_idx)
    ioi = [round(local[idx + 1][0] - local[idx][0], 3) for idx in range(len(local) - 1) if local[idx + 1][0] > local[idx][0]]
    median_ioi = sorted(ioi)[len(ioi) // 2] if ioi else 0.0
    ratios = [round(value / median_ioi, 3) for value in ioi[:8]] if median_ioi > 0 else []
    confidence = min(0.95, 0.3 + (note_count / 80.0) + (0.15 if len(set(onset_positions)) >= 4 else 0.0))
    return {
        "quantization_grid_seconds": round(float(grid), 6),
        "quantization_confidence": round(float(confidence), 6),
        "token_pattern": "".join(tokens),
        "accent_pattern": "".join(accents),
        "limitations": [],
        "onset_positions": sorted(set(onset_positions)),
        "velocity_pattern": velocities[:16],
        "ioi_seconds": ioi[:12],
        "ratio_pattern": ratios,
    }


def _collect_subpatterns(pattern: str, min_len: int, max_len: int) -> dict[str, list[int]]:
    output: dict[str, list[int]] = defaultdict(list)
    if not pattern:
        return output
    for width in range(min_len, max_len + 1):
        if len(pattern) < width:
            continue
        for idx in range(0, len(pattern) - width + 1):
            sub = pattern[idx : idx + width]
            if sub.count("x") + sub.count("X") < 2:
                continue
            output[sub].append(idx)
    return output


def _collect_sequence_ngrams(values: list[float], min_len: int, max_len: int) -> dict[str, list[int]]:
    output: dict[str, list[int]] = defaultdict(list)
    for width in range(min_len, max_len + 1):
        if len(values) < width:
            continue
        for idx in range(0, len(values) - width + 1):
            chunk = tuple(round(values[idx + offset], 3) for offset in range(width))
            key = "|".join(f"{item:.3f}" for item in chunk)
            output[key].append(idx)
    return output


def extract_rhythm_features(
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
        window_id: str | None = None,
        segment_id: str | None = None,
        region_id: str | None = None,
    ) -> None:
        feature_values = rhythm_feature_vector(global_events, start_seconds=start_seconds, end_seconds=end_seconds)
        note_count = int(feature_values.get("note_on_count", 0) or 0)
        confidence = 0.9 if source_mode == "merged" else 0.72
        confidence = min(confidence, 0.35 + min(0.6, note_count / 120.0))
        record_limitations: list[str] = []
        if source_mode == "window_fallback":
            record_limitations.append("window fallback used because merged MIDI was unavailable.")
        if note_count < 8:
            confidence = min(confidence, 0.45)
            record_limitations.append("low event count; rhythm estimates are low confidence.")
        if float(feature_values.get("estimated_pulse_seconds", 0.0) or 0.0) == 0.0:
            confidence = min(confidence, 0.35)
            record_limitations.append("insufficient IOI evidence for stable tempo estimation.")
        record = rhythm_feature_record(
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
        record["record_id"] = f"{performance_id}:{segment_run_id}:{granularity}:{len(records):04d}"
        if segment_id is not None:
            record["segment_id"] = segment_id
        if region_id is not None:
            record["region_id"] = region_id
        annotate_feature_record_with_rhythm_concepts(record)
        records.append(record)
        confidence_scores.append(confidence)

    # Performance-level summary
    _append_record(granularity="performance", start_seconds=0.0, end_seconds=duration_seconds)

    # Segment-level records
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

    # Window-level records
    for window in windows:
        start = float(window.get("core_start_seconds", 0.0) or 0.0)
        end = float(window.get("core_end_seconds", start) or start)
        _append_record(
            granularity="window",
            window_id=str(window.get("window_id", "")),
            start_seconds=start,
            end_seconds=end,
        )

    # Fixed-bin rhythm regions
    for index, (bin_start, bin_end) in enumerate(build_time_bins(0.0, duration_seconds, bin_seconds=bin_seconds)):
        _append_record(
            granularity="rhythm_region",
            region_id=f"rhythm_region_{index:04d}",
            start_seconds=bin_start,
            end_seconds=bin_end,
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

    # Multi-resolution motif candidates from record-local token/IOI patterns.
    motif_candidates: list[dict[str, object]] = []
    motif_key_to_idx: dict[str, int] = {}
    motif_occurrences: dict[str, list[float]] = defaultdict(list)
    motif_groups: dict[str, dict[str, object]] = {}
    repeated_accent_patterns: Counter[str] = Counter()
    straight_grid_count = 0
    triplet_grid_count = 0
    irregular_region_count = 0
    steady_region_count = 0
    for record in records:
        granularity = str(record.get("granularity", ""))
        if granularity not in {"performance", "segment", "window", "rhythm_region"}:
            continue
        features = record.get("features", {})
        if not isinstance(features, dict):
            continue
        start_seconds = float(record.get("start_seconds", 0.0) or 0.0)
        end_seconds = float(record.get("end_seconds", start_seconds) or start_seconds)
        quantized = _tokenize_region(
            global_events,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            pulse_seconds=float(features.get("estimated_pulse_seconds", 0.0) or 0.0),
            note_count=int(features.get("note_on_count", 0) or 0),
        )
        features.update(
            {
                "quantization_grid_seconds": quantized["quantization_grid_seconds"],
                "quantization_confidence": quantized["quantization_confidence"],
                "token_pattern": quantized["token_pattern"],
                "accent_pattern": quantized["accent_pattern"],
            }
        )
        if float(features.get("syncopation_proxy_score", 0.0) or 0.0) <= 0.16:
            steady_region_count += 1
        if float(features.get("syncopation_proxy_score", 0.0) or 0.0) >= 0.30:
            irregular_region_count += 1
        token_pattern = str(quantized["token_pattern"])
        accent_pattern = str(quantized["accent_pattern"])
        if "x..x..x" in token_pattern or "X..x..x" in token_pattern:
            triplet_grid_count += 1
        if "x.x.x.x" in token_pattern or "X.x.x.x" in token_pattern:
            straight_grid_count += 1
        if accent_pattern:
            repeated_accent_patterns[accent_pattern] += 1
        token_ngrams = _collect_subpatterns(token_pattern, 3, 12)
        accent_ngrams = _collect_subpatterns(accent_pattern, 3, 12)
        ioi_values = [float(item) for item in (quantized.get("ioi_seconds", []) or [])]
        ratio_values = [float(item) for item in (quantized.get("ratio_pattern", []) or [])]
        ioi_ngrams = _collect_sequence_ngrams(ioi_values, 3, 8)
        ratio_ngrams = _collect_sequence_ngrams(ratio_values, 3, 8)
        for token_key, positions in token_ngrams.items():
            if len(positions) < 2:
                continue
            group_key = f"token:{token_key}"
            motif_occurrences[group_key].append(start_seconds)
            if group_key not in motif_key_to_idx:
                motif_key_to_idx[group_key] = len(motif_candidates)
                motif_candidates.append(
                    {
                        "motif_id": f"motif_{len(motif_candidates):04d}",
                        "granularity": granularity,
                        "source_record_id": record.get("record_id"),
                        "region_id": record.get("region_id"),
                        "window_id": record.get("window_id"),
                        "start_seconds": start_seconds,
                        "end_seconds": end_seconds,
                        "token_pattern": token_key,
                        "ioi_pattern_seconds": [],
                        "normalized_ratio_pattern": [],
                        "repeat_count": len(positions),
                        "occurrence_times": [round(start_seconds + idx * float(quantized["quantization_grid_seconds"]), 3) for idx in positions[:8]],
                        "confidence": round(min(0.95, 0.25 + len(positions) / 6.0), 6),
                        "evidence": {"mode": "token_ngram", "positions": positions[:8]},
                        "rhythm_concepts": ["motif", "repetition", "cycle"],
                        "philosophy_sources": ["cycle", "geometry"],
                        "detection_targets": ["token_pattern", "motif_recurrence", "circular_pattern_similarity"],
                        "limitations": ["heuristic token n-gram motif extraction."],
                    }
                )
            group = motif_groups.setdefault(
                group_key,
                {
                    "motif_group_id": f"motif_group_{len(motif_groups):04d}",
                    "group_repeat_count": 0,
                    "representative_pattern": token_key,
                    "occurrence_count": 0,
                    "region_ids": [],
                    "window_ids": [],
                    "rhythm_concepts": ["motif", "repetition", "cycle"],
                    "philosophy_sources": ["cycle", "geometry"],
                    "detection_targets": ["token_pattern", "motif_recurrence"],
                },
            )
            group["group_repeat_count"] = int(group.get("group_repeat_count", 0)) + len(positions)
            group["occurrence_count"] = int(group.get("occurrence_count", 0)) + 1
            if record.get("region_id"):
                group["region_ids"].append(record.get("region_id"))
            if record.get("window_id"):
                group["window_ids"].append(record.get("window_id"))
        for key, positions in accent_ngrams.items():
            if len(positions) >= 2:
                repeated_accent_patterns[key] += len(positions)
        for seq_map, mode in [(ioi_ngrams, "ioi_ngram"), (ratio_ngrams, "ratio_ngram")]:
            for seq_key, positions in seq_map.items():
                if len(positions) < 2:
                    continue
                full_key = f"{mode}:{seq_key}"
                motif_occurrences[full_key].append(start_seconds)
                if full_key not in motif_key_to_idx:
                    motif_key_to_idx[full_key] = len(motif_candidates)
                    motif_candidates.append(
                        {
                            "motif_id": f"motif_{len(motif_candidates):04d}",
                            "granularity": granularity,
                            "source_record_id": record.get("record_id"),
                            "region_id": record.get("region_id"),
                            "window_id": record.get("window_id"),
                            "start_seconds": start_seconds,
                            "end_seconds": end_seconds,
                            "token_pattern": token_pattern[:24],
                            "ioi_pattern_seconds": [float(x) for x in seq_key.split("|")] if mode == "ioi_ngram" else [],
                            "normalized_ratio_pattern": [float(x) for x in seq_key.split("|")] if mode == "ratio_ngram" else [],
                            "repeat_count": len(positions),
                            "occurrence_times": [round(start_seconds + idx * float(quantized["quantization_grid_seconds"]), 3) for idx in positions[:8]],
                            "confidence": round(min(0.95, 0.28 + len(positions) / 7.0), 6),
                            "evidence": {"mode": mode, "positions": positions[:8]},
                            "rhythm_concepts": ["motif", "repetition", "cycle"],
                            "philosophy_sources": ["cycle", "geometry"],
                            "detection_targets": ["ioi_pattern", "motif_recurrence"],
                            "limitations": ["heuristic sequence n-gram motif extraction."],
                        }
                    )
                group = motif_groups.setdefault(
                    full_key,
                    {
                        "motif_group_id": f"motif_group_{len(motif_groups):04d}",
                        "group_repeat_count": 0,
                        "representative_pattern": seq_key,
                        "occurrence_count": 0,
                        "region_ids": [],
                        "window_ids": [],
                        "rhythm_concepts": ["motif", "repetition", "geometry"],
                        "philosophy_sources": ["geometry", "cycle"],
                        "detection_targets": ["ioi_pattern", "rotation_equivalence"],
                    },
                )
                group["group_repeat_count"] = int(group.get("group_repeat_count", 0)) + len(positions)
                group["occurrence_count"] = int(group.get("occurrence_count", 0)) + 1
                if record.get("region_id"):
                    group["region_ids"].append(record.get("region_id"))
                if record.get("window_id"):
                    group["window_ids"].append(record.get("window_id"))

    motif_candidates = sorted(motif_candidates, key=lambda item: (int(item.get("repeat_count", 0)), float(item.get("confidence", 0.0))), reverse=True)
    for idx, motif in enumerate(motif_candidates):
        motif["motif_id"] = f"motif_{idx:04d}"
    motif_group_list = sorted(
        [
            {
                **group,
                "group_repeat_count": int(group.get("group_repeat_count", 0)),
                "occurrence_count": int(group.get("occurrence_count", 0)),
                "region_ids": sorted({str(item) for item in group.get("region_ids", []) if item}),
                "window_ids": sorted({str(item) for item in group.get("window_ids", []) if item}),
            }
            for group in motif_groups.values()
            if int(group.get("group_repeat_count", 0)) >= 2
        ],
        key=lambda item: (int(item.get("group_repeat_count", 0)), int(item.get("occurrence_count", 0))),
        reverse=True,
    )
    rhythm_family_counts: dict[str, int] = {}
    top_family_matches: list[dict[str, object]] = []
    unknown_high_information_patterns: list[dict[str, object]] = []
    for motif in motif_candidates:
        classification = classify_rhythm_pattern(motif)
        motif["rhythm_lexicon_matches"] = [classification] if classification else []
        motif["best_rhythm_family_match"] = classification.get("matched_family")
        motif["rhythm_family_confidence"] = classification.get("confidence", 0.0)
    for group in motif_group_list:
        classification = classify_rhythm_pattern(
            {
                "token_pattern": group.get("representative_pattern", ""),
                "accent_pattern": group.get("representative_pattern", ""),
                "normalized_ratio_pattern": [],
            }
        )
        group["rhythm_lexicon_matches"] = [classification] if classification else []
        group["best_rhythm_family_match"] = classification.get("matched_family")
        group["rhythm_family_confidence"] = classification.get("confidence", 0.0)
        family = str(classification.get("matched_family", "unknown"))
        if float(classification.get("confidence", 0.0) or 0.0) >= 0.58 and family and family != "unknown":
            rhythm_family_counts[family] = rhythm_family_counts.get(family, 0) + int(group.get("group_repeat_count", 0) or 0)
            if len(top_family_matches) < 24:
                top_family_matches.append(
                    {
                        "motif_group_id": group.get("motif_group_id"),
                        "matched_family": family,
                        "matched_pattern_id": classification.get("matched_pattern_id"),
                        "confidence": classification.get("confidence"),
                        "representative_pattern": group.get("representative_pattern"),
                        "occurrence_count": group.get("occurrence_count"),
                    }
                )
        info_score = int(group.get("group_repeat_count", 0) or 0) + int(group.get("occurrence_count", 0) or 0)
        if float(classification.get("confidence", 0.0) or 0.0) < 0.5 and info_score >= 8:
            unknown_high_information_patterns.append(
                {
                    "motif_group_id": group.get("motif_group_id"),
                    "representative_pattern": group.get("representative_pattern"),
                    "information_score": info_score,
                    "best_candidate_family": classification.get("matched_family"),
                    "best_candidate_confidence": classification.get("confidence"),
                }
            )

    rhythm_pattern_index = {
        "motif_count": len(motif_candidates),
        "motif_group_count": len(motif_group_list),
        "top_motif_groups": motif_group_list[:10],
        "repeated_accent_patterns": [
            {"pattern": key, "count": int(value)}
            for key, value in repeated_accent_patterns.most_common(12)
            if key and value >= 2
        ],
        "dense_burst_patterns": [
            item
            for item in motif_group_list
            if "x" in str(item.get("representative_pattern", "")).lower() and int(item.get("group_repeat_count", 0)) >= 4
        ][:10],
        "sparse_call_response_candidates": [
            item
            for item in motif_group_list
            if "." in str(item.get("representative_pattern", "")) and int(item.get("group_repeat_count", 0)) >= 3
        ][:10],
        "steady_pulse_regions": steady_region_count,
        "irregular_regions": irregular_region_count,
        "straight_grid_candidates": straight_grid_count,
        "triplet_grid_candidates": triplet_grid_count,
        "rhythm_family_counts": rhythm_family_counts,
        "top_rhythm_family_matches": sorted(top_family_matches, key=lambda item: float(item.get("confidence", 0.0) or 0.0), reverse=True)[:20],
        "unknown_high_information_patterns": sorted(
            unknown_high_information_patterns,
            key=lambda item: int(item.get("information_score", 0) or 0),
            reverse=True,
        )[:20],
        "concept_counts": concept_count([record for record in records if isinstance(record, dict)]),
        "philosophy_source_counts": philosophy_count([record for record in records if isinstance(record, dict)]),
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
        feature_version="rhythm_pack_v1",
        extractor_name="rhythm_feature_extractor_v1",
        confidence=pack_confidence,
        limitations=limitations,
        summary=summary,
        records=records,
    )
    payload["generated_at"] = now_iso()
    payload["rhythm_motifs"] = {
        "motif_count": len(motif_candidates),
        "motifs": motif_candidates,
    }
    payload["rhythm_motif_groups"] = motif_group_list
    payload["rhythm_pattern_index"] = rhythm_pattern_index
    output_path = target_dir / "rhythm_features.json"
    save_json(output_path, payload)
    return output_path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract rhythm features from active performance artifacts.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    parser.add_argument("--output-dir", default=None, help="Optional output folder for feature files")
    parser.add_argument("--bin-seconds", type=float, default=4.0)
    args = parser.parse_args()
    output_dir = Path(args.output_dir) if args.output_dir else None
    output_path = extract_rhythm_features(
        Path(args.performance_manifest),
        output_dir=output_dir,
        bin_seconds=args.bin_seconds,
    )
    print(f"RHYTHM_FEATURES_PATH={output_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
