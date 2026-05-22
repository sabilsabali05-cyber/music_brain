from __future__ import annotations

import argparse
from dataclasses import dataclass
import math
import sys
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from features.rhythm_time.meter_time_schema import base_payload
except ModuleNotFoundError:  # pragma: no cover
    from rhythm_time.meter_time_schema import base_payload  # type: ignore

try:
    from scripts.feature_dataset_common import (
        collect_global_events,
        default_feature_dir,
        events_in_range,
        get_active_paths,
        load_json,
        performance_metadata,
        save_json,
    )
except ModuleNotFoundError:  # pragma: no cover
    from feature_dataset_common import (  # type: ignore
        collect_global_events,
        default_feature_dir,
        events_in_range,
        get_active_paths,
        load_json,
        performance_metadata,
        save_json,
    )


@dataclass
class Region:
    region_id: str
    start_seconds: float
    end_seconds: float
    source: str


def _safe_float(value: object, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:  # noqa: BLE001
        return fallback


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _round(value: float) -> float:
    return round(float(value), 6)


def _ioi_values(events: list[tuple[float, int, int]]) -> list[float]:
    return [b[0] - a[0] for a, b in zip(events, events[1:]) if b[0] > a[0]]


def _median_or_zero(values: list[float]) -> float:
    return float(median(values)) if values else 0.0


def _stability_from_ioi(ioi_values: list[float], pulse_seconds: float) -> float:
    if len(ioi_values) < 2 or pulse_seconds <= 0:
        return 0.0
    spread = pstdev(ioi_values)
    normalized = spread / max(pulse_seconds, 1e-6)
    return _clamp01(1.0 - normalized)


def infer_subdivision_type(ioi_values: list[float], pulse_seconds: float) -> dict[str, float | str]:
    if pulse_seconds <= 0 or len(ioi_values) < 3:
        return {
            "subdivision_type": "sparse",
            "grid_confidence": 0.15,
            "ambiguity": 0.9,
            "straightness": 0.0,
            "tripletness": 0.0,
            "swingness": 0.0,
            "randomness": 1.0,
        }
    ratios = [value / pulse_seconds for value in ioi_values if value > 0]
    if len(ratios) < 3:
        return {
            "subdivision_type": "free",
            "grid_confidence": 0.2,
            "ambiguity": 0.85,
            "straightness": 0.0,
            "tripletness": 0.0,
            "swingness": 0.0,
            "randomness": 1.0,
        }

    def _score(targets: list[float]) -> float:
        penalties: list[float] = []
        for ratio in ratios:
            nearest = min(abs(ratio - target) for target in targets)
            penalties.append(nearest)
        avg_penalty = mean(penalties) if penalties else 1.0
        return _clamp01(1.0 - min(1.0, avg_penalty))

    straightness = _score([0.5, 1.0, 2.0])
    tripletness = _score([1.0 / 3.0, 2.0 / 3.0, 1.0, 4.0 / 3.0])
    swingness = _score([2.0 / 3.0, 1.0 / 3.0, 1.0, 4.0 / 3.0])
    randomness = _clamp01((pstdev(ratios) if len(ratios) > 1 else 1.0) / 0.6)

    ranked = sorted(
        [
            ("straight", straightness),
            ("triplet", tripletness),
            ("swing", swingness),
            ("free", 1.0 - randomness),
        ],
        key=lambda item: item[1],
        reverse=True,
    )
    top_name, top_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0
    ambiguity = _clamp01(1.0 - (top_score - second_score))
    grid_confidence = _clamp01((top_score * 0.75) + ((1.0 - randomness) * 0.25))
    if randomness > 0.8:
        top_name = "random"
        grid_confidence = min(grid_confidence, 0.45)
        ambiguity = max(ambiguity, 0.75)

    return {
        "subdivision_type": top_name,
        "grid_confidence": _round(grid_confidence),
        "ambiguity": _round(ambiguity),
        "straightness": _round(straightness),
        "tripletness": _round(tripletness),
        "swingness": _round(swingness),
        "randomness": _round(randomness),
    }


def _collect_regions(segments_manifest: dict[str, Any], duration_seconds: float) -> list[Region]:
    output: list[Region] = []
    windows = segments_manifest.get("transcription_windows", [])
    if isinstance(windows, list):
        for item in windows:
            if not isinstance(item, dict):
                continue
            if str(item.get("status", "pending")) != "success":
                continue
            start = _safe_float(item.get("core_start_seconds"), 0.0)
            end = _safe_float(item.get("core_end_seconds"), start)
            if end <= start:
                continue
            output.append(
                Region(
                    region_id=str(item.get("window_id", f"window_{len(output):04d}")),
                    start_seconds=start,
                    end_seconds=end,
                    source="window",
                )
            )
    segments = segments_manifest.get("musical_segments", [])
    if isinstance(segments, list):
        for idx, item in enumerate(segments):
            if not isinstance(item, dict):
                continue
            start = _safe_float(item.get("global_start_seconds"), 0.0)
            end = _safe_float(item.get("global_end_seconds"), start)
            if end <= start:
                continue
            output.append(
                Region(
                    region_id=str(item.get("segment_id", f"segment_{idx:04d}")),
                    start_seconds=start,
                    end_seconds=end,
                    source="segment",
                )
            )
    if not output and duration_seconds > 0:
        bucket = max(12.0, min(48.0, duration_seconds / 8.0))
        cursor = 0.0
        index = 0
        while cursor < duration_seconds:
            nxt = min(duration_seconds, cursor + bucket)
            output.append(Region(region_id=f"region_{index:04d}", start_seconds=cursor, end_seconds=nxt, source="fallback"))
            cursor = nxt
            index += 1
    return output


def _meter_candidates() -> list[tuple[str, int, int]]:
    return [("4/4", 4, 4), ("3/4", 3, 4), ("6/8", 6, 8), ("12/8", 12, 8), ("5/4", 5, 4), ("7/8", 7, 8)]


def _meter_hypotheses(
    events: list[tuple[float, int, int]],
    *,
    start_seconds: float,
    pulse_seconds: float,
) -> list[dict[str, Any]]:
    if pulse_seconds <= 0 or len(events) < 8:
        return [
            {
                "hypothesis_id": "meter_h_0000",
                "meter": "undetermined",
                "beats_per_bar": 0,
                "beat_unit": 0,
                "confidence": 0.15,
                "ambiguity": 0.9,
                "evidence": {"reason": "insufficient events or unstable pulse"},
                "limitations": ["insufficient evidence for bar-level meter inference."],
            }
        ]
    velocities = [float(item[2]) for item in events]
    accent_cutoff = mean(velocities) + (pstdev(velocities) * 0.4 if len(velocities) > 1 else 0.0)
    scored: list[dict[str, Any]] = []
    for meter, beats_per_bar, beat_unit in _meter_candidates():
        bar_len = pulse_seconds * beats_per_bar
        if bar_len <= 0:
            continue
        downbeat_hits = 0.0
        offbeat_hits = 0.0
        bar_count = 0
        downbeat_offsets: list[float] = []
        for event_time, _, velocity in events:
            rel = max(0.0, event_time - start_seconds)
            bar_index = int(rel / bar_len) if bar_len > 0 else 0
            beat_phase = (rel - (bar_index * bar_len)) / pulse_seconds
            beat_slot = int(round(beat_phase)) % max(1, beats_per_bar)
            if beat_slot == 0:
                downbeat_hits += 1.0 + (0.3 if velocity >= accent_cutoff else 0.0)
                downbeat_offsets.append(abs(beat_phase - round(beat_phase)))
            else:
                offbeat_hits += 1.0 + (0.2 if velocity >= accent_cutoff else 0.0)
            bar_count = max(bar_count, bar_index + 1)
        ratio = downbeat_hits / max(1.0, offbeat_hits)
        offset_penalty = mean(downbeat_offsets) if downbeat_offsets else 0.5
        consistency = _clamp01(1.0 - offset_penalty)
        bar_support = _clamp01(bar_count / 6.0)
        confidence = _clamp01((ratio / 2.5) * 0.45 + consistency * 0.35 + bar_support * 0.2)
        scored.append(
            {
                "meter": meter,
                "beats_per_bar": beats_per_bar,
                "beat_unit": beat_unit,
                "confidence": confidence,
                "evidence": {
                    "downbeat_hits": round(downbeat_hits, 4),
                    "offbeat_hits": round(offbeat_hits, 4),
                    "bar_support": round(bar_support, 4),
                    "consistency": round(consistency, 4),
                },
            }
        )
    scored.sort(key=lambda item: float(item.get("confidence", 0.0)), reverse=True)
    top = float(scored[0].get("confidence", 0.0)) if scored else 0.0
    second = float(scored[1].get("confidence", 0.0)) if len(scored) > 1 else 0.0
    ambiguity = _clamp01(1.0 - (top - second))
    output: list[dict[str, Any]] = []
    for idx, item in enumerate(scored[:4]):
        output.append(
            {
                "hypothesis_id": f"meter_h_{idx:04d}",
                "meter": item.get("meter"),
                "beats_per_bar": int(item.get("beats_per_bar", 0) or 0),
                "beat_unit": int(item.get("beat_unit", 0) or 0),
                "confidence": _round(float(item.get("confidence", 0.0) or 0.0)),
                "ambiguity": _round(ambiguity),
                "evidence": item.get("evidence", {}),
                "limitations": ["meter is multi-hypothesis and remains probabilistic."],
            }
        )
    return output


def _cycle_pattern(
    events: list[tuple[float, int, int]],
    *,
    start_seconds: float,
    end_seconds: float,
    pulse_seconds: float,
    subdivision_type: str,
) -> dict[str, Any]:
    if pulse_seconds <= 0 or len(events) < 16:
        return {
            "cycle_id": "cycle_0000",
            "start_seconds": _round(start_seconds),
            "end_seconds": _round(end_seconds),
            "cycle_length_beats": 0.0,
            "confidence": 0.2,
            "ambiguity": 0.85,
            "supporting_subdivision": subdivision_type,
            "evidence": {"reason": "insufficient events for cycle detection"},
            "limitations": ["cycle detection requires repeated onset density patterns."],
        }
    beat_count = max(1, int((end_seconds - start_seconds) / pulse_seconds))
    series = [0.0] * beat_count
    for time_value, _, velocity in events:
        idx = int((time_value - start_seconds) / pulse_seconds)
        if 0 <= idx < beat_count:
            series[idx] += 1.0 + (float(velocity) / 127.0) * 0.2
    if sum(series) <= 0:
        return {
            "cycle_id": "cycle_0000",
            "start_seconds": _round(start_seconds),
            "end_seconds": _round(end_seconds),
            "cycle_length_beats": 0.0,
            "confidence": 0.2,
            "ambiguity": 0.9,
            "supporting_subdivision": subdivision_type,
            "evidence": {"reason": "empty onset series"},
            "limitations": ["cycle detection failed due to empty onset series."],
        }
    center = mean(series)
    den = sum((value - center) ** 2 for value in series)
    best_lag = 0
    best_score = 0.0
    for lag in range(2, min(24, len(series) // 2 + 1)):
        num = 0.0
        for idx in range(len(series) - lag):
            num += (series[idx] - center) * (series[idx + lag] - center)
        corr = num / den if den > 0 else 0.0
        if corr > best_score:
            best_score = corr
            best_lag = lag
    confidence = _clamp01((best_score + 0.1) / 1.1)
    ambiguity = _clamp01(1.0 - confidence)
    return {
        "cycle_id": "cycle_0000",
        "start_seconds": _round(start_seconds),
        "end_seconds": _round(end_seconds),
        "cycle_length_beats": _round(float(best_lag)),
        "confidence": _round(confidence),
        "ambiguity": _round(ambiguity),
        "supporting_subdivision": subdivision_type,
        "evidence": {
            "autocorrelation_peak": _round(best_score),
            "series_length_beats": len(series),
        },
        "limitations": ["cycle confidence drops when density changes rapidly across sections."],
    }


def _macro_section_name(
    *,
    start_seconds: float,
    end_seconds: float,
    duration_seconds: float,
    mean_density: float,
    tag_names: list[str],
) -> str:
    midpoint = (start_seconds + end_seconds) / 2.0
    ratio = midpoint / max(duration_seconds, 1e-6)
    lowered_tags = " ".join(tag_names).lower()
    if "outro" in lowered_tags or ratio >= 0.9:
        return "outro_or_coda"
    if "intro" in lowered_tags or ratio <= 0.1:
        return "intro_or_prelude"
    if "bridge" in lowered_tags:
        return "bridge_or_breakdown"
    if mean_density >= 5.0:
        return "climactic_peak"
    if mean_density <= 1.5:
        return "sparse_break_or_interlude"
    return "verse_or_chorus_candidate"


def extract_meter_time_features(
    performance_manifest_path: Path,
    *,
    output_dir: Path | None = None,
) -> tuple[Path, Path]:
    performance_manifest = load_json(performance_manifest_path)
    segments_manifest_path, analysis_path, merged_midi_path = get_active_paths(performance_manifest)
    if not segments_manifest_path.exists():
        raise FileNotFoundError(f"Active segments manifest missing: {segments_manifest_path}")
    segments_manifest = load_json(segments_manifest_path)
    performance_id, source_name, segment_run_id = performance_metadata(performance_manifest, segments_manifest_path)
    target_dir = (output_dir or default_feature_dir(performance_id, segment_run_id)) / "rhythm_time"
    target_dir.mkdir(parents=True, exist_ok=True)

    feature_dir = (output_dir or default_feature_dir(performance_id, segment_run_id)).resolve()
    rhythm_path = feature_dir / "rhythm_features.json"
    harmony_path = feature_dir / "harmony_features.json"
    tags_path = feature_dir / "tags.json"
    routing_path = feature_dir / "routing" / "analysis_routing_decisions.json"
    reliability_path = feature_dir / "trust" / "transcription_reliability.json"
    rhythm_payload = load_json(rhythm_path) if rhythm_path.exists() else {}
    harmony_payload = load_json(harmony_path) if harmony_path.exists() else {}
    tags_payload = load_json(tags_path) if tags_path.exists() else {}
    routing_payload = load_json(routing_path) if routing_path.exists() else {}
    reliability_payload = load_json(reliability_path) if reliability_path.exists() else {}

    global_events, source_mode, source_limitations = collect_global_events(
        segments_manifest=segments_manifest,
        merged_midi_path=merged_midi_path,
    )
    duration_seconds = _safe_float(
        performance_manifest.get("duration_seconds")
        or segments_manifest.get("duration_seconds")
        or (global_events[-1][0] if global_events else 0.0),
        0.0,
    )
    regions = _collect_regions(segments_manifest, duration_seconds)
    limitations = list(source_limitations)

    microtiming_records: list[dict[str, Any]] = []
    subdivision_grid_records: list[dict[str, Any]] = []
    phrase_rhythm_records: list[dict[str, Any]] = []
    tempo_values: list[float] = []
    stability_values: list[float] = []
    grid_conf_values: list[float] = []
    subdivision_counts: dict[str, int] = {}
    tag_rows = tags_payload.get("tags", []) if isinstance(tags_payload.get("tags"), list) else []

    for idx, region in enumerate(regions):
        local_events = events_in_range(global_events, start_seconds=region.start_seconds, end_seconds=region.end_seconds)
        ioi = _ioi_values(local_events)
        pulse_seconds = _median_or_zero(ioi)
        local_tempo_bpm = 60.0 / pulse_seconds if pulse_seconds > 0 else 0.0
        pulse_stability = _stability_from_ioi(ioi, pulse_seconds)
        subdivision = infer_subdivision_type(ioi, pulse_seconds)
        subdivision_type = str(subdivision.get("subdivision_type", "free"))
        subdivision_counts[subdivision_type] = subdivision_counts.get(subdivision_type, 0) + 1
        grid_confidence = _safe_float(subdivision.get("grid_confidence"), 0.0)
        ambiguity = _safe_float(subdivision.get("ambiguity"), 1.0)

        residuals: list[float] = []
        if pulse_seconds > 0 and local_events:
            if subdivision_type in {"triplet", "swing"}:
                step = pulse_seconds / 3.0
            else:
                step = pulse_seconds / 2.0
            for event_time, _, _ in local_events:
                rel = max(0.0, event_time - region.start_seconds)
                nearest = round(rel / max(step, 1e-6)) * step
                residuals.append(rel - nearest)
        bias_ms = mean(residuals) * 1000.0 if residuals else 0.0
        jitter_ms = pstdev(residuals) * 1000.0 if len(residuals) > 1 else 0.0
        micro_summary = (
            f"{subdivision_type} feel, jitter {jitter_ms:.1f}ms, bias {bias_ms:+.1f}ms, "
            f"stability {pulse_stability:.2f}"
        )

        microtiming_records.append(
            {
                "record_id": f"micro_{idx:04d}",
                "start_seconds": _round(region.start_seconds),
                "end_seconds": _round(region.end_seconds),
                "local_tempo_bpm": _round(local_tempo_bpm),
                "pulse_stability": _round(pulse_stability),
                "microtiming_bias_ms": _round(bias_ms),
                "microtiming_jitter_ms": _round(jitter_ms),
                "microtiming_summary": micro_summary,
                "confidence": _round((pulse_stability * 0.6) + (grid_confidence * 0.4)),
                "ambiguity": _round(max(ambiguity, 1.0 - pulse_stability)),
                "limitations": (
                    ["low event count in region."]
                    if len(local_events) < 8
                    else ["heuristic microtiming estimate from symbolic events."]
                ),
            }
        )
        subdivision_grid_records.append(
            {
                "record_id": f"grid_{idx:04d}",
                "start_seconds": _round(region.start_seconds),
                "end_seconds": _round(region.end_seconds),
                "local_tempo_bpm": _round(local_tempo_bpm),
                "subdivision_type": subdivision_type,
                "grid_confidence": _round(grid_confidence),
                "ambiguity": _round(ambiguity),
                "straightness": _safe_float(subdivision.get("straightness"), 0.0),
                "tripletness": _safe_float(subdivision.get("tripletness"), 0.0),
                "swingness": _safe_float(subdivision.get("swingness"), 0.0),
                "randomness": _safe_float(subdivision.get("randomness"), 1.0),
                "limitations": (
                    ["sparse timing evidence; subdivision remains tentative."]
                    if len(ioi) < 4
                    else ["subdivision inferred from IOI ratio clustering."]
                ),
            }
        )

        phrase_span_beats = ((region.end_seconds - region.start_seconds) / pulse_seconds) if pulse_seconds > 0 else 0.0
        half_time = (region.start_seconds + region.end_seconds) / 2.0
        first_half = events_in_range(global_events, start_seconds=region.start_seconds, end_seconds=half_time)
        second_half = events_in_range(global_events, start_seconds=half_time, end_seconds=region.end_seconds)
        first_density = len(first_half) / max(half_time - region.start_seconds, 1e-6)
        second_density = len(second_half) / max(region.end_seconds - half_time, 1e-6)
        if first_density == 0 and second_density == 0:
            phrase_shape = "free_or_silent"
        elif second_density > first_density * 1.2:
            phrase_shape = "expanding"
        elif first_density > second_density * 1.2:
            phrase_shape = "contracting"
        else:
            phrase_shape = "stable"
        phrase_rhythm_records.append(
            {
                "phrase_id": f"phrase_{idx:04d}",
                "start_seconds": _round(region.start_seconds),
                "end_seconds": _round(region.end_seconds),
                "phrase_span_beats": _round(phrase_span_beats),
                "phrase_shape": phrase_shape,
                "pulse_stability": _round(pulse_stability),
                "confidence": _round((pulse_stability + grid_confidence) / 2.0),
                "ambiguity": _round(max(ambiguity, 0.2 if phrase_shape != "free_or_silent" else 0.8)),
                "evidence": {
                    "region_source": region.source,
                    "event_count": len(local_events),
                    "first_half_density": _round(first_density),
                    "second_half_density": _round(second_density),
                },
                "limitations": ["phrase boundaries are proxy regions from windows/segments."],
            }
        )
        if local_tempo_bpm > 0:
            tempo_values.append(local_tempo_bpm)
        stability_values.append(pulse_stability)
        grid_conf_values.append(grid_confidence)

    global_pulse = _median_or_zero(_ioi_values(global_events))
    hypotheses = _meter_hypotheses(global_events, start_seconds=0.0, pulse_seconds=global_pulse)
    best_subdivision = max(subdivision_counts.items(), key=lambda item: item[1])[0] if subdivision_counts else "free"
    cycle_record = _cycle_pattern(
        global_events,
        start_seconds=0.0,
        end_seconds=duration_seconds,
        pulse_seconds=global_pulse,
        subdivision_type=best_subdivision,
    )

    macro_records: list[dict[str, Any]] = []
    for idx, region in enumerate(regions[: max(1, min(len(regions), 16))]):
        local_events = events_in_range(global_events, start_seconds=region.start_seconds, end_seconds=region.end_seconds)
        ioi = _ioi_values(local_events)
        pulse_seconds = _median_or_zero(ioi)
        local_tempo_bpm = 60.0 / pulse_seconds if pulse_seconds > 0 else 0.0
        pulse_stability = _stability_from_ioi(ioi, pulse_seconds)
        density = len(local_events) / max(region.end_seconds - region.start_seconds, 1e-6)
        region_tags = [
            str(item.get("tag", ""))
            for item in tag_rows
            if isinstance(item, dict)
            and _safe_float(item.get("start_seconds"), region.start_seconds) <= region.end_seconds
            and _safe_float(item.get("end_seconds"), region.end_seconds) >= region.start_seconds
        ]
        macro_name = _macro_section_name(
            start_seconds=region.start_seconds,
            end_seconds=region.end_seconds,
            duration_seconds=max(duration_seconds, 1e-6),
            mean_density=density,
            tag_names=region_tags,
        )
        macro_records.append(
            {
                "macro_id": f"macro_{idx:04d}",
                "start_seconds": _round(region.start_seconds),
                "end_seconds": _round(region.end_seconds),
                "macro_section_candidate": macro_name,
                "local_tempo_bpm": _round(local_tempo_bpm),
                "pulse_stability": _round(pulse_stability),
                "confidence": _round((pulse_stability * 0.4) + (0.3 if region_tags else 0.0) + 0.2),
                "ambiguity": _round(0.7 if not region_tags else 0.45),
                "evidence": {
                    "tag_refs": region_tags[:6],
                    "event_density": _round(density),
                },
                "limitations": ["macro section labels are candidates, not annotated ground truth."],
            }
        )

    confidence_values = [
        _safe_float(item.get("confidence"), 0.0)
        for item in (microtiming_records + subdivision_grid_records + hypotheses + [cycle_record] + phrase_rhythm_records + macro_records)
        if isinstance(item, dict)
    ]
    ambiguity_values = [
        _safe_float(item.get("ambiguity"), 1.0)
        for item in (microtiming_records + subdivision_grid_records + hypotheses + [cycle_record] + phrase_rhythm_records + macro_records)
        if isinstance(item, dict)
    ]
    overall_conf = _round(mean(confidence_values) if confidence_values else 0.0)
    overall_amb = _round(mean(ambiguity_values) if ambiguity_values else 1.0)
    if not global_events:
        limitations.append("no MIDI timeline available for meter/time extraction.")
    if overall_conf < 0.45:
        limitations.append("meter/time remains low-confidence; treat as weak evidence.")
    summary = {
        "source_mode": source_mode,
        "event_count": len(global_events),
        "region_count": len(regions),
        "local_tempo_bpm_median": _round(_median_or_zero(tempo_values)),
        "pulse_stability_mean": _round(mean(stability_values) if stability_values else 0.0),
        "grid_confidence_mean": _round(mean(grid_conf_values) if grid_conf_values else 0.0),
        "subdivision_histogram": subdivision_counts,
        "top_meter_hypothesis": hypotheses[0] if hypotheses else {},
        "meter_hypothesis_count": len(hypotheses),
        "cycle_length_beats": cycle_record.get("cycle_length_beats"),
        "macro_section_candidates": sorted({str(item.get("macro_section_candidate", "")) for item in macro_records if item.get("macro_section_candidate")}),
    }
    payload = base_payload(
        performance_id=performance_id,
        source_name=source_name,
        segment_run_id=segment_run_id,
        source_artifact_paths={
            "performance_manifest_path": performance_manifest_path.resolve().as_posix(),
            "analysis_path": analysis_path.resolve().as_posix() if analysis_path else None,
            "segments_manifest_path": segments_manifest_path.resolve().as_posix(),
            "merged_midi_path": merged_midi_path.resolve().as_posix() if merged_midi_path and merged_midi_path.exists() else None,
            "rhythm_features_path": rhythm_path.resolve().as_posix() if rhythm_path.exists() else None,
            "harmony_features_path": harmony_path.resolve().as_posix() if harmony_path.exists() else None,
            "tags_path": tags_path.resolve().as_posix() if tags_path.exists() else None,
            "routing_path": routing_path.resolve().as_posix() if routing_path.exists() else None,
            "reliability_path": reliability_path.resolve().as_posix() if reliability_path.exists() else None,
        },
        confidence=overall_conf,
        ambiguity=overall_amb,
        limitations=limitations,
        summary=summary,
        microtiming_records=microtiming_records,
        subdivision_grid_records=subdivision_grid_records,
        beat_meter_hypotheses=hypotheses,
        cycle_pattern_records=[cycle_record],
        phrase_rhythm_records=phrase_rhythm_records,
        macro_time_records=macro_records,
    )
    payload["routing_snapshot"] = routing_payload.get("summary", {}) if isinstance(routing_payload, dict) else {}
    payload["reliability_snapshot"] = reliability_payload.get("summary", {}) if isinstance(reliability_payload, dict) else {}
    json_path = target_dir / "meter_time_features.json"
    save_json(json_path, payload)

    lines = [
        f"# Meter and Time Summary - {performance_id}",
        "",
        f"- source_mode: `{source_mode}`",
        f"- overall_confidence: `{overall_conf}`",
        f"- overall_ambiguity: `{overall_amb}`",
        f"- event_count: `{len(global_events)}`",
        f"- local_tempo_bpm_median: `{summary['local_tempo_bpm_median']}`",
        f"- pulse_stability_mean: `{summary['pulse_stability_mean']}`",
        f"- grid_confidence_mean: `{summary['grid_confidence_mean']}`",
        f"- subdivision_histogram: `{summary['subdivision_histogram']}`",
        "",
        "## Meter Hypotheses",
    ]
    for item in hypotheses[:4]:
        lines.append(
            f"- `{item.get('meter')}` confidence=`{item.get('confidence')}` "
            f"ambiguity=`{item.get('ambiguity')}` evidence=`{item.get('evidence')}`"
        )
    lines.extend(
        [
            "",
            "## Cycle Pattern",
            f"- cycle_length_beats: `{cycle_record.get('cycle_length_beats')}`",
            f"- confidence: `{cycle_record.get('confidence')}` ambiguity: `{cycle_record.get('ambiguity')}`",
            "",
            "## Phrase Rhythm",
        ]
    )
    for item in phrase_rhythm_records[:8]:
        lines.append(
            f"- `{item.get('phrase_id')}` shape=`{item.get('phrase_shape')}` "
            f"beats=`{item.get('phrase_span_beats')}` stability=`{item.get('pulse_stability')}`"
        )
    lines.extend(["", "## Macro Time"])
    for item in macro_records[:8]:
        lines.append(
            f"- `{item.get('macro_id')}` section=`{item.get('macro_section_candidate')}` "
            f"tempo=`{item.get('local_tempo_bpm')}` confidence=`{item.get('confidence')}`"
        )
    lines.extend(["", "## Limitations"])
    for limitation in limitations:
        lines.append(f"- {limitation}")
    md_path = target_dir / "meter_time_summary.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path.resolve(), md_path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract hierarchical meter/time features from existing performance artifacts.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    parser.add_argument("--output-dir", default=None, help="Optional output folder for feature files")
    args = parser.parse_args()
    output_dir = Path(args.output_dir) if args.output_dir else None
    json_path, md_path = extract_meter_time_features(Path(args.performance_manifest), output_dir=output_dir)
    print(f"METER_TIME_FEATURES_PATH={json_path.as_posix()}")
    print(f"METER_TIME_SUMMARY_PATH={md_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
