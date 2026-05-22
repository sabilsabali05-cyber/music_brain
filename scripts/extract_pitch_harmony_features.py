from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any

from mido import MidiFile

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.pitch_harmony.pitch_harmony_schema import (  # noqa: E402
    ChordMovementRecord,
    CounterpointRecord,
    HarmonySonorityRecord,
    IntervalRecord,
    MelodyContourRecord,
    PitchHarmonyMacroRecord,
    PitchObservationRecord,
    TuningSystemRecord,
)
from features.schema import performance_feature_pack  # noqa: E402
from scripts.feature_dataset_common import (  # noqa: E402
    build_time_bins,
    collect_global_events,
    collect_midi_sources,
    default_feature_dir,
    events_in_range,
    get_active_paths,
    load_json,
    now_iso,
    performance_metadata,
    save_json,
)


def _pc_name(pc: int) -> str:
    return ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"][pc % 12]


def _interval_hist(values: list[int]) -> dict[str, int]:
    hist: dict[str, int] = {}
    for value in values:
        key = str(int(value))
        hist[key] = hist.get(key, 0) + 1
    return hist


def classify_sonority_type(pitch_classes: list[int]) -> str:
    pcs = sorted(set(int(item) % 12 for item in pitch_classes))
    if len(pcs) <= 1:
        return "single_pitch_or_drone_candidate"
    if len(pcs) >= 5 and any(((pcs[(idx + 1) % len(pcs)] - pcs[idx]) % 12) <= 2 for idx in range(len(pcs) - 1)):
        return "cluster_sonority_candidate"
    for root in range(12):
        if {(root + 0) % 12, (root + 4) % 12, (root + 7) % 12}.issubset(set(pcs)) or {
            (root + 0) % 12,
            (root + 3) % 12,
            (root + 7) % 12,
        }.issubset(set(pcs)):
            return "triadic_sonority_candidate"
    for root in range(12):
        if {(root + 0) % 12, (root + 5) % 12, (root + 10) % 12}.issubset(set(pcs)):
            return "quartal_sonority_candidate"
    if len(pcs) >= 6:
        return "extended_or_color_sonority_candidate"
    return "ambiguous_or_nonfunctional_sonority_candidate"


def _motion_metrics(root_intervals: list[int], interval_classes: list[int]) -> dict[str, float]:
    total = max(1, len(root_intervals))
    return {
        "stepwise_motion_score": round(sum(1 for item in root_intervals if item in {1, 2, 10, 11}) / total, 6),
        "chromatic_motion_score": round(sum(1 for item in root_intervals if item in {1, 11}) / total, 6),
        "circle_motion_score": round(sum(1 for item in root_intervals if item in {5, 7}) / total, 6),
        "tritone_motion_score": round(sum(1 for item in root_intervals if item == 6) / total, 6),
        "seconds_cluster_score": round(sum(1 for item in interval_classes if item in {1, 2}) / max(1, len(interval_classes)), 6),
    }


def _extract_pitch_bend_count(midi_paths: list[Path]) -> int:
    count = 0
    for midi_path in midi_paths:
        if not midi_path.exists():
            continue
        midi = MidiFile(str(midi_path))
        for track in midi.tracks:
            for msg in track:
                if msg.type == "pitchwheel" and int(getattr(msg, "pitch", 0)) != 0:
                    count += 1
    return count


def _window_slice(
    events: list[tuple[float, int, int]],
    *,
    start_seconds: float,
    end_seconds: float,
) -> dict[str, Any]:
    local = events_in_range(events, start_seconds=start_seconds, end_seconds=end_seconds)
    duration = max(0.0, end_seconds - start_seconds)
    notes = [int(note) for _, note, _ in local]
    velocities = [int(vel) for _, _, vel in local]
    pcs = [note % 12 for note in notes]
    pitch_hist = [0] * 12
    for pc in pcs:
        pitch_hist[pc] += 1
    pc_total = max(1, sum(pitch_hist))
    pc_summary = {str(idx): round(value / pc_total, 6) for idx, value in enumerate(pitch_hist) if value > 0}
    centers = sorted([(idx, value / pc_total) for idx, value in enumerate(pitch_hist)], key=lambda item: item[1], reverse=True)[:5]
    melodic_intervals = [notes[idx + 1] - notes[idx] for idx in range(len(notes) - 1)]
    melodic_mod = [value % 12 for value in melodic_intervals]
    interval_class = [min(abs(value) % 12, 12 - (abs(value) % 12)) for value in melodic_intervals if value != 0]
    contour_tokens = "".join(
        "U" if delta > 0 else ("D" if delta < 0 else "S")
        for delta in melodic_intervals[:64]
    )
    ioi = [round(local[idx + 1][0] - local[idx][0], 4) for idx in range(len(local) - 1) if local[idx + 1][0] > local[idx][0]]
    cadence_candidates: list[dict[str, Any]] = []
    if notes:
        final_pc = notes[-1] % 12
        if centers and final_pc == centers[0][0]:
            cadence_candidates.append(
                {
                    "type": "arrival_on_local_pitch_center_candidate",
                    "time_seconds": round(end_seconds, 6),
                    "confidence": round(min(0.92, 0.45 + centers[0][1]), 6),
                }
            )
    sonority_type = classify_sonority_type(pcs)
    voicing_span = float(max(notes) - min(notes)) if notes else 0.0
    root_guess = centers[0][0] if centers else 0
    root_motion = [((melodic_mod[idx]) % 12) for idx in range(len(melodic_mod))]
    movement_metrics = _motion_metrics(root_motion, interval_class)
    counterpoint_contrary = 0.0
    if len(notes) >= 6:
        upper = notes[::2]
        lower = notes[1::2]
        paired = min(len(upper), len(lower)) - 1
        if paired > 0:
            contrary = 0
            for idx in range(paired):
                up_move = upper[idx + 1] - upper[idx]
                low_move = lower[idx + 1] - lower[idx]
                if up_move * low_move < 0:
                    contrary += 1
            counterpoint_contrary = contrary / paired
    return {
        "events": local,
        "notes": notes,
        "velocities": velocities,
        "pitch_hist": pitch_hist,
        "pitch_class_summary": pc_summary,
        "pitch_centers": centers,
        "melodic_intervals": melodic_intervals,
        "interval_class": interval_class,
        "contour_tokens": contour_tokens or "S",
        "ioi": ioi,
        "cadence_candidates": cadence_candidates,
        "sonority_type": sonority_type,
        "voicing_span": voicing_span,
        "root_guess": root_guess,
        "root_motion": root_motion,
        "movement_metrics": movement_metrics,
        "counterpoint_contrary": round(float(counterpoint_contrary), 6),
        "duration": duration,
    }


def extract_pitch_harmony_features(performance_manifest_path: Path, *, output_dir: Path | None = None) -> Path:
    performance_manifest = load_json(performance_manifest_path)
    segments_manifest_path, analysis_path, merged_midi_path = get_active_paths(performance_manifest)
    if not segments_manifest_path.exists():
        raise FileNotFoundError(f"Active segments manifest missing: {segments_manifest_path}")
    segments_manifest = load_json(segments_manifest_path)
    performance_id, source_name, segment_run_id = performance_metadata(performance_manifest, segments_manifest_path)
    feature_dir = output_dir or default_feature_dir(performance_id, segment_run_id)
    out_dir = feature_dir / "pitch_harmony"
    out_dir.mkdir(parents=True, exist_ok=True)
    rhythm_path = feature_dir / "rhythm_features.json"
    harmony_path = feature_dir / "harmony_features.json"
    tags_path = feature_dir / "tags.json"
    routing_dir = feature_dir / "routing"
    reliability_path = feature_dir / "trust" / "transcription_reliability.json"
    context_artifacts: dict[str, Any] = {}
    for key, path in [
        ("rhythm_features_path", rhythm_path),
        ("harmony_features_path", harmony_path),
        ("tags_path", tags_path),
        ("routing_asset_classification_path", routing_dir / "asset_classification.json"),
        ("routing_content_regions_path", routing_dir / "content_region_routes.json"),
        ("routing_decisions_path", routing_dir / "analysis_routing_decisions.json"),
        ("transcription_reliability_path", reliability_path),
    ]:
        if path.exists():
            context_artifacts[key] = path.resolve().as_posix()
            try:
                context_artifacts[key.replace("_path", "_summary")] = load_json(path).get("summary", {})
            except Exception:  # noqa: BLE001
                continue

    global_events, source_mode, source_limitations = collect_global_events(
        segments_manifest=segments_manifest,
        merged_midi_path=merged_midi_path,
    )
    duration_seconds = float(
        performance_manifest.get("duration_seconds")
        or segments_manifest.get("duration_seconds")
        or (global_events[-1][0] if global_events else 0.0)
    )

    windows = segments_manifest.get("transcription_windows", [])
    if not isinstance(windows, list):
        windows = []
    bins = build_time_bins(0.0, duration_seconds, bin_seconds=4.0)
    slices: list[tuple[str, str, float, float]] = [("performance", "performance", 0.0, duration_seconds)]
    for idx, window in enumerate(windows):
        if not isinstance(window, dict) or str(window.get("status", "")) != "success":
            continue
        start = float(window.get("core_start_seconds", 0.0) or 0.0)
        end = float(window.get("core_end_seconds", start) or start)
        slices.append(("window", str(window.get("window_id") or f"window_{idx:04d}"), start, end))
    for idx, (start, end) in enumerate(bins):
        slices.append(("region", f"region_{idx:04d}", start, end))

    sources, _, _ = collect_midi_sources(segments_manifest=segments_manifest, merged_midi_path=merged_midi_path)
    midi_paths = [source.path for source in sources if source.path.exists()]
    pitch_bend_count = _extract_pitch_bend_count(midi_paths)
    microtonal_evidence_type = "unavailable"
    microtonal_confidence = 0.0
    microtonal_analysis_available = False
    tuning_limitations: list[str] = []
    if pitch_bend_count > 0:
        microtonal_evidence_type = "pitch_bend"
        microtonal_confidence = min(0.9, 0.35 + pitch_bend_count / 100.0)
        microtonal_analysis_available = True
    elif global_events:
        microtonal_evidence_type = "external_analyzer_required"
        microtonal_confidence = 0.15
        tuning_limitations.append("No direct non-12TET evidence in symbolic MIDI; audio tuning estimator required.")
    else:
        tuning_limitations.append("No symbolic events available for tuning evidence.")

    pitch_records: list[dict[str, Any]] = []
    interval_records: list[dict[str, Any]] = []
    contour_records: list[dict[str, Any]] = []
    sonority_records: list[dict[str, Any]] = []
    movement_records: list[dict[str, Any]] = []
    counterpoint_records: list[dict[str, Any]] = []
    tuning_records: list[dict[str, Any]] = []

    recurring_sonority_counter: Counter[str] = Counter()
    confidence_scores: list[float] = []

    for granularity, label, start, end in slices:
        sl = _window_slice(global_events, start_seconds=start, end_seconds=end)
        note_count = len(sl["notes"])
        confidence = min(0.95, 0.25 + note_count / 120.0)
        limitations: list[str] = []
        if source_mode != "merged":
            limitations.append("Merged MIDI unavailable; derived from window fallback timeline.")
        if note_count < 8:
            confidence = min(confidence, 0.45)
            limitations.append("Low symbolic note count; interpretive labels are tentative.")
        recurring_sonority_counter[sl["sonority_type"]] += 1
        confidence_scores.append(confidence)
        base_evidence = {"granularity": granularity, "slice_id": label, "event_count": note_count}

        pitch_records.append(
            PitchObservationRecord(
                performance_id=performance_id,
                source_name=source_name,
                segment_run_id=segment_run_id,
                start_seconds=start,
                end_seconds=end,
                confidence=confidence,
                limitations=limitations,
                pitch_range={
                    "min_midi": min(sl["notes"]) if sl["notes"] else None,
                    "max_midi": max(sl["notes"]) if sl["notes"] else None,
                    "semitones": (max(sl["notes"]) - min(sl["notes"])) if sl["notes"] else 0,
                },
                register_distribution={
                    "low": sum(1 for n in sl["notes"] if n < 48),
                    "mid": sum(1 for n in sl["notes"] if 48 <= n < 72),
                    "high": sum(1 for n in sl["notes"] if n >= 72),
                },
                pitch_class_histogram={"counts": sl["pitch_hist"], "normalized": sl["pitch_class_summary"]},
                pitch_center_candidates=[
                    {"pitch_class": _pc_name(pc), "pc_index": int(pc), "score": round(float(score), 6)}
                    for pc, score in sl["pitch_centers"]
                ],
                pitch_stability_salience={
                    "top_pitch_class_ratio": round(float(sl["pitch_centers"][0][1]), 6) if sl["pitch_centers"] else 0.0,
                    "velocity_mean": round(sum(sl["velocities"]) / max(1, len(sl["velocities"])), 6) if sl["velocities"] else 0.0,
                },
                microtonal_placeholders={
                    "microtonal_analysis_available": microtonal_analysis_available,
                    "microtonal_evidence_type": microtonal_evidence_type,
                },
                evidence=base_evidence,
            )
        )

        interval_records.append(
            IntervalRecord(
                performance_id=performance_id,
                source_name=source_name,
                segment_run_id=segment_run_id,
                start_seconds=start,
                end_seconds=end,
                confidence=confidence,
                limitations=limitations,
                melodic_interval_distribution=_interval_hist(sl["melodic_intervals"]),
                harmonic_interval_distribution={},
                interval_class_histogram=_interval_hist(sl["interval_class"]),
                interval_family_metrics={
                    "step_vs_leap_ratio": round(
                        sum(1 for v in sl["melodic_intervals"] if abs(v) <= 2) / max(1, len(sl["melodic_intervals"])), 6
                    ),
                    "cluster_seconds_score": sl["movement_metrics"]["seconds_cluster_score"],
                    "fourth_fifth_score": round(
                        sum(1 for v in sl["melodic_intervals"] if abs(v) % 12 in {5, 7}) / max(1, len(sl["melodic_intervals"])),
                        6,
                    ),
                    "tritone_score": sl["movement_metrics"]["tritone_motion_score"],
                    "chromatic_score": sl["movement_metrics"]["chromatic_motion_score"],
                },
                evidence=base_evidence,
            )
        )

        contour_records.append(
            MelodyContourRecord(
                performance_id=performance_id,
                source_name=source_name,
                segment_run_id=segment_run_id,
                start_seconds=start,
                end_seconds=end,
                confidence=confidence,
                limitations=limitations,
                contour_tokens=sl["contour_tokens"],
                contour_shape_candidates=[
                    {
                        "label": "ascending_tendency_candidate"
                        if sl["contour_tokens"].count("U") > sl["contour_tokens"].count("D")
                        else "descending_or_balanced_candidate",
                        "score": round(abs(sl["contour_tokens"].count("U") - sl["contour_tokens"].count("D")) / max(1, len(sl["contour_tokens"])), 6),
                    }
                ],
                phrase_movement_summary={
                    "up_moves": sl["contour_tokens"].count("U"),
                    "down_moves": sl["contour_tokens"].count("D"),
                    "static_moves": sl["contour_tokens"].count("S"),
                },
                motif_sequence_candidates=[
                    {"token_fragment": sl["contour_tokens"][idx : idx + 4], "count": sl["contour_tokens"].count(sl["contour_tokens"][idx : idx + 4])}
                    for idx in range(0, max(0, len(sl["contour_tokens"]) - 3), 4)
                    if len(sl["contour_tokens"][idx : idx + 4]) == 4
                ][:5],
                cadence_arrival_candidates=sl["cadence_candidates"],
                evidence=base_evidence,
            )
        )

        sonority_records.append(
            HarmonySonorityRecord(
                performance_id=performance_id,
                source_name=source_name,
                segment_run_id=segment_run_id,
                start_seconds=start,
                end_seconds=end,
                confidence=confidence,
                limitations=limitations + ["Sonority candidates are not treated as hard chord truths."],
                pitch_class_set=[idx for idx, count in enumerate(sl["pitch_hist"]) if count > 0],
                voicing_span_semitones=sl["voicing_span"],
                sonority_type_candidate=sl["sonority_type"],
                sonority_hypotheses=[
                    {"label": sl["sonority_type"], "confidence": round(confidence, 6)},
                    {"label": "cluster_color_candidate" if len([v for v in sl["interval_class"] if v <= 2]) >= 3 else "non_cluster_candidate", "confidence": round(min(0.8, confidence * 0.9), 6)},
                ],
                chord_candidates=[
                    {
                        "label": f"{_pc_name(sl['root_guess'])}_centered_candidate",
                        "confidence": round(min(0.78, confidence * 0.85), 6),
                        "candidate_only": True,
                    }
                ],
                extension_alteration_candidates=["possible_added_tones_or_alterations"] if len(set(sl["notes"])) >= 5 else [],
                evidence=base_evidence,
            )
        )

        root_intervals = [int(item) % 12 for item in sl["root_motion"]]
        movement_records.append(
            ChordMovementRecord(
                performance_id=performance_id,
                source_name=source_name,
                segment_run_id=segment_run_id,
                start_seconds=start,
                end_seconds=end,
                confidence=confidence,
                limitations=limitations + ["Movement/cadence/modulation outputs are hypotheses only."],
                root_motion_candidates=[{"interval": value, "count": count} for value, count in _interval_hist(root_intervals).items()],
                bass_motion_candidates=[],
                common_tone_count=sum(1 for a, b in zip(sl["notes"], sl["notes"][1:]) if (a % 12) == (b % 12)),
                voice_leading_proxy={
                    "average_abs_melodic_motion": round(sum(abs(v) for v in sl["melodic_intervals"]) / max(1, len(sl["melodic_intervals"])), 6),
                    "stepwise_ratio": sl["movement_metrics"]["stepwise_motion_score"],
                },
                movement_metrics=sl["movement_metrics"],
                cadence_modulation_candidates=[
                    {
                        "label": "possible_authentic_or_plagal_arrival_candidate",
                        "confidence": round(min(0.7, confidence * 0.8), 6),
                    }
                ]
                if sl["cadence_candidates"]
                else [],
                evidence=base_evidence,
            )
        )

        counterpoint_records.append(
            CounterpointRecord(
                performance_id=performance_id,
                source_name=source_name,
                segment_run_id=segment_run_id,
                start_seconds=start,
                end_seconds=end,
                confidence=confidence,
                limitations=limitations + ["Counterpoint estimates are symbolic-motion proxies."],
                voice_count_estimate=max(1, min(6, int(round((len(sl["notes"]) / max(1.0, sl["duration"])) * 0.6)))),
                motion_proxy_summary={
                    "contrary_motion_proxy": sl["counterpoint_contrary"],
                    "parallel_motion_proxy": round(max(0.0, 1.0 - sl["counterpoint_contrary"]), 6),
                },
                imitation_call_response_candidates=[
                    {"label": "possible_call_response_candidate", "confidence": round(min(0.65, 0.25 + len(sl["ioi"]) / 30.0), 6)}
                ]
                if len(sl["ioi"]) >= 3
                else [],
                independence_summary={
                    "rhythmic_independence_proxy": round(min(1.0, len(set(sl["ioi"])) / 6.0), 6) if sl["ioi"] else 0.0,
                    "pitch_independence_proxy": round(min(1.0, len(set(sl["notes"])) / 12.0), 6) if sl["notes"] else 0.0,
                },
                evidence=base_evidence,
            )
        )

        tuning_records.append(
            TuningSystemRecord(
                performance_id=performance_id,
                source_name=source_name,
                segment_run_id=segment_run_id,
                start_seconds=start,
                end_seconds=end,
                confidence=min(confidence, 0.72),
                limitations=limitations + tuning_limitations,
                microtonal_analysis_available=microtonal_analysis_available,
                microtonal_evidence_type=microtonal_evidence_type,
                microtonal_confidence=microtonal_confidence,
                tuning_hypotheses=[
                    {"label": "12tet_compatible_candidate", "confidence": round(max(0.3, 1.0 - microtonal_confidence), 6)},
                    {"label": "microtonal_or_detuned_candidate", "confidence": round(microtonal_confidence, 6)},
                    {"label": "no_clear_tuning_system_candidate", "confidence": 0.3},
                ],
                evidence=base_evidence,
            )
        )

    macro_limitations = list(source_limitations)
    if not microtonal_analysis_available:
        macro_limitations.append("Microtonal certainty unavailable without external audio tuning analysis.")
    overall_conf = round(sum(confidence_scores) / max(1, len(confidence_scores)), 6)
    key_hypotheses = [
        {"label": "tonal_center_candidate", "confidence": round(min(0.8, overall_conf), 6)},
        {"label": "modal_or_mixture_candidate", "confidence": 0.45},
        {"label": "ambiguous_or_no_clear_tonal_center", "confidence": round(max(0.2, 1.0 - overall_conf), 6)},
        {"label": "nonfunctional_or_cluster_color_candidate", "confidence": 0.3},
    ]
    macro_record = PitchHarmonyMacroRecord(
        performance_id=performance_id,
        source_name=source_name,
        segment_run_id=segment_run_id,
        start_seconds=0.0,
        end_seconds=duration_seconds,
        confidence=overall_conf,
        limitations=macro_limitations,
        key_hypotheses=key_hypotheses,
        recurring_sonority_families=[
            {"label": name, "count": int(count)}
            for name, count in recurring_sonority_counter.most_common(6)
        ],
        register_density_arc={
            "total_event_count": len(global_events),
            "avg_note_density_per_second": round(len(global_events) / max(1.0, duration_seconds), 6),
        },
        dissonance_cluster_arc={
            "seconds_interval_share": round(
                sum(
                    int(record["interval_family_metrics"]["cluster_seconds_score"] > 0.2)
                    for record in interval_records
                )
                / max(1, len(interval_records)),
                6,
            ),
        },
        macro_form_candidates=[
            {"label": "sectional_density_arc_candidate", "confidence": 0.5},
            {"label": "cyclic_recurrence_candidate", "confidence": 0.4},
            {"label": "through_composed_or_free_form_candidate", "confidence": 0.35},
        ],
        evidence={"source_mode": source_mode},
    )

    payload = performance_feature_pack(
        performance_id=performance_id,
        source_name=source_name,
        segment_run_id=segment_run_id,
        source_artifact_paths={
            "performance_manifest_path": performance_manifest_path.resolve().as_posix(),
            "segments_manifest_path": segments_manifest_path.resolve().as_posix(),
            "analysis_path": analysis_path.resolve().as_posix() if analysis_path and analysis_path.exists() else None,
            "merged_midi_path": merged_midi_path.resolve().as_posix() if merged_midi_path and merged_midi_path.exists() else None,
        },
        feature_version="pitch_harmony_pack_v1",
        extractor_name="pitch_harmony_feature_extractor_v1",
        confidence=overall_conf,
        limitations=macro_limitations,
        summary={
            "source_mode": source_mode,
            "slice_count": len(slices),
            "microtonal_analysis_available": microtonal_analysis_available,
            "microtonal_evidence_type": microtonal_evidence_type,
            "microtonal_confidence": round(microtonal_confidence, 6),
        },
        records=[],
    )
    payload["generated_at"] = now_iso()
    payload["context_artifacts"] = context_artifacts
    payload["pitch_observations"] = pitch_records
    payload["interval_analysis"] = interval_records
    payload["melody_contour"] = contour_records
    payload["harmony_sonority"] = sonority_records
    payload["chord_movement"] = movement_records
    payload["counterpoint"] = counterpoint_records
    payload["tuning_system"] = tuning_records
    payload["macro_record"] = macro_record
    payload["key_hypotheses"] = key_hypotheses
    payload["microtonal_analysis_available"] = microtonal_analysis_available
    payload["microtonal_evidence_type"] = microtonal_evidence_type
    payload["microtonal_confidence"] = round(microtonal_confidence, 6)

    output_json = out_dir / "pitch_harmony_features.json"
    save_json(output_json, payload)

    summary_lines = [
        f"# Pitch/Harmony Summary - {performance_id}",
        "",
        f"- segment_run_id: `{segment_run_id}`",
        f"- source_mode: `{source_mode}`",
        f"- pitch_observation_count: `{len(pitch_records)}`",
        f"- interval_record_count: `{len(interval_records)}`",
        f"- sonority_record_count: `{len(sonority_records)}`",
        f"- counterpoint_record_count: `{len(counterpoint_records)}`",
        f"- microtonal_analysis_available: `{microtonal_analysis_available}`",
        f"- microtonal_evidence_type: `{microtonal_evidence_type}`",
        f"- microtonal_confidence: `{round(microtonal_confidence, 6)}`",
        "",
        "## Key Hypotheses",
    ]
    for item in key_hypotheses:
        summary_lines.append(f"- `{item['label']}` confidence=`{item['confidence']}`")
    summary_lines.extend(["", "## Recurring Sonority Families"])
    for item in macro_record["recurring_sonority_families"]:
        summary_lines.append(f"- `{item['label']}` count=`{item['count']}`")
    summary_lines.extend(
        [
            "",
            "## Limitations",
            "- Chord/key/mode/cadence/modulation outputs are candidates only.",
            "- Non-12TET conclusions require direct evidence; otherwise remain limited.",
        ]
    )
    (out_dir / "pitch_harmony_summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    return output_json.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract hierarchical pitch/harmony/tuning intelligence features.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    args = parser.parse_args()
    output = extract_pitch_harmony_features(Path(args.performance_manifest))
    print(f"PITCH_HARMONY_FEATURES_PATH={output.as_posix()}")
    print(f"PITCH_HARMONY_SUMMARY_PATH={(output.parent / 'pitch_harmony_summary.md').as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
