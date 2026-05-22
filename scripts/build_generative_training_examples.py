from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

from mido import MidiFile, merge_tracks, tick2second

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.generative.generative_schema import generative_example
from features.generative.task_policies import TASK_POLICIES
from features.model_sources import MODEL_SOURCES
from features.theory_sources import THEORY_SOURCES
from scripts.feature_dataset_common import load_json, now_iso, resolve_artifact_performance_dir, save_json
from scripts.trust_common import resolve_performance_context


DEFAULT_TASKS = [
    "continuation",
    "phrase_continuation",
    "groove_continuation",
    "harmony_continuation",
    "melody_continuation",
    "call_response",
    "motif_transformation",
    "section_transition",
    "buildup_to_release",
    "infill_missing_region",
]

NON_SILENCE_STATES = {
    "rhythm_dominant",
    "percussive_only",
    "harmonic_dominant",
    "melodic_lead",
    "vocal_dominant",
    "rap_vocal_dominant",
    "polyphonic_full_mix",
}


def _safe_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = load_json(path)
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:  # noqa: BLE001
        return fallback


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _score_density(note_count: int, duration_seconds: float) -> float:
    density = note_count / max(1e-6, duration_seconds)
    if density <= 0.1:
        return 0.1
    if density <= 0.4:
        return 0.35
    if density <= 1.5:
        return 0.7
    if density <= 6.0:
        return 0.9
    return 0.65


def _load_note_events(midi_path: Path | None) -> list[dict[str, float]]:
    if midi_path is None or not midi_path.exists():
        return []
    try:
        midi = MidiFile(midi_path.as_posix())
    except Exception:  # noqa: BLE001
        return []
    events: list[dict[str, float]] = []
    tempo = 500000
    now_sec = 0.0
    active: dict[tuple[int, int], list[tuple[float, int]]] = {}
    merged = merge_tracks(midi.tracks)
    for message in merged:
        now_sec += tick2second(message.time, midi.ticks_per_beat, tempo)
        if message.type == "set_tempo":
            tempo = int(getattr(message, "tempo", tempo))
            continue
        if message.type == "note_on" and int(getattr(message, "velocity", 0)) > 0:
            key = (int(getattr(message, "channel", 0)), int(getattr(message, "note", 0)))
            active.setdefault(key, []).append((now_sec, int(getattr(message, "velocity", 0))))
            continue
        if message.type in {"note_off", "note_on"}:
            vel = int(getattr(message, "velocity", 0))
            if message.type == "note_on" and vel > 0:
                continue
            key = (int(getattr(message, "channel", 0)), int(getattr(message, "note", 0)))
            queue = active.get(key, [])
            if not queue:
                continue
            start, velocity = queue.pop(0)
            if not queue:
                active.pop(key, None)
            end = max(start + 1e-4, now_sec)
            events.append(
                {
                    "start": round(start, 6),
                    "end": round(end, 6),
                    "note": float(key[1]),
                    "velocity": float(velocity),
                }
            )
    return sorted(events, key=lambda item: item["start"])


def _events_in_range(events: list[dict[str, float]], start_seconds: float, end_seconds: float) -> list[dict[str, float]]:
    output: list[dict[str, float]] = []
    for event in events:
        if event["end"] < start_seconds:
            continue
        if event["start"] > end_seconds:
            break
        output.append(event)
    return output


def _segment_windows(segments_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    windows = segments_manifest.get("transcription_windows", [])
    if not isinstance(windows, list):
        return []
    output: list[dict[str, Any]] = []
    for idx, window in enumerate(windows):
        if not isinstance(window, dict):
            continue
        start = _safe_float(window.get("core_start_seconds"), _safe_float(window.get("global_start_seconds"), 0.0))
        end = _safe_float(window.get("core_end_seconds"), _safe_float(window.get("global_end_seconds"), start))
        if end <= start:
            continue
        item = {
            "window_id": str(window.get("window_id", f"win_{idx:04d}")),
            "index": int(window.get("index", idx) or idx),
            "start_seconds": start,
            "end_seconds": end,
            "duration_seconds": end - start,
            "midi_path": str(window.get("midi_path") or "").strip() or None,
            "status": str(window.get("status", "unknown")),
        }
        output.append(item)
    return sorted(output, key=lambda row: (row["start_seconds"], row["end_seconds"]))


def _segments(segments_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    segments = segments_manifest.get("musical_segments", [])
    if not isinstance(segments, list):
        return []
    output: list[dict[str, Any]] = []
    for idx, segment in enumerate(segments):
        if not isinstance(segment, dict):
            continue
        start = _safe_float(segment.get("global_start_seconds"), 0.0)
        end = _safe_float(segment.get("global_end_seconds"), start)
        if end <= start:
            continue
        output.append(
            {
                "segment_id": str(segment.get("segment_id", f"seg_{idx:04d}")),
                "index": int(segment.get("index", idx) or idx),
                "start_seconds": start,
                "end_seconds": end,
                "duration_seconds": end - start,
                "section_label": str(segment.get("section_label", "")),
                "phrase_label": str(segment.get("phrase_label", "")),
            }
        )
    return sorted(output, key=lambda row: (row["start_seconds"], row["end_seconds"]))


def _build_routing_lookup(feature_dir: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, str | None]]:
    routing_dir = feature_dir / "routing"
    routes_payload = _safe_json(routing_dir / "content_region_routes.json")
    decisions_payload = _safe_json(routing_dir / "analysis_routing_decisions.json")
    routes = routes_payload.get("routes", [])
    decisions = decisions_payload.get("decisions", [])
    route_rows = [row for row in routes if isinstance(row, dict)]
    decision_by_source: dict[str, dict[str, Any]] = {}
    for row in decisions if isinstance(decisions, list) else []:
        if not isinstance(row, dict):
            continue
        decision_by_source[str(row.get("source_record_id", ""))] = row
    refs = {
        "content_region_routes": (routing_dir / "content_region_routes.json").resolve().as_posix() if (routing_dir / "content_region_routes.json").exists() else None,
        "analysis_routing_decisions": (routing_dir / "analysis_routing_decisions.json").resolve().as_posix() if (routing_dir / "analysis_routing_decisions.json").exists() else None,
    }
    return route_rows, decision_by_source, refs


def _dominant_content_state(
    *,
    start_seconds: float,
    end_seconds: float,
    route_rows: list[dict[str, Any]],
) -> tuple[str, float]:
    overlap_by_state: Counter[str] = Counter()
    known_overlap_by_state: Counter[str] = Counter()
    best_conf = 0.0
    for route in route_rows:
        r_start = _safe_float(route.get("start_seconds"), 0.0)
        r_end = _safe_float(route.get("end_seconds"), r_start)
        overlap = max(0.0, min(end_seconds, r_end) - max(start_seconds, r_start))
        if overlap <= 0:
            continue
        state = str(route.get("content_state", "unknown"))
        overlap_by_state[state] += overlap
        if state != "unknown":
            known_overlap_by_state[state] += overlap
        best_conf = max(best_conf, _safe_float(route.get("confidence"), 0.0))
    if not overlap_by_state:
        return "unknown", 0.0
    if known_overlap_by_state:
        state, _ = known_overlap_by_state.most_common(1)[0]
    else:
        state, _ = overlap_by_state.most_common(1)[0]
    return state, round(best_conf, 6)


def _build_reliability_lookup(feature_dir: Path) -> dict[str, dict[str, Any]]:
    payload = _safe_json(feature_dir / "trust" / "transcription_reliability.json")
    windows = payload.get("windows", [])
    output: dict[str, dict[str, Any]] = {}
    for row in windows if isinstance(windows, list) else []:
        if not isinstance(row, dict):
            continue
        output[str(row.get("window_id", ""))] = row
    return output


def _build_meter_summary(feature_dir: Path) -> dict[str, Any]:
    payload = _safe_json(feature_dir / "rhythm_time" / "meter_time_features.json")
    return {
        "path": (feature_dir / "rhythm_time" / "meter_time_features.json").resolve().as_posix() if (feature_dir / "rhythm_time" / "meter_time_features.json").exists() else None,
        "summary": payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {},
        "meter_hypotheses": payload.get("beat_meter_hypotheses", [])[:3] if isinstance(payload.get("beat_meter_hypotheses"), list) else [],
        "ambiguity": _safe_float(payload.get("ambiguity"), 1.0),
        "confidence": _safe_float(payload.get("confidence"), 0.0),
        "phrase_rhythm_records": payload.get("phrase_rhythm_records", []) if isinstance(payload.get("phrase_rhythm_records"), list) else [],
        "macro_time_records": payload.get("macro_time_records", []) if isinstance(payload.get("macro_time_records"), list) else [],
    }


def _build_pitch_summary(feature_dir: Path) -> dict[str, Any]:
    payload = _safe_json(feature_dir / "pitch_harmony" / "pitch_harmony_features.json")
    return {
        "path": (feature_dir / "pitch_harmony" / "pitch_harmony_features.json").resolve().as_posix() if (feature_dir / "pitch_harmony" / "pitch_harmony_features.json").exists() else None,
        "summary": payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {},
        "macro_record": payload.get("macro_record", {}) if isinstance(payload.get("macro_record"), dict) else {},
        "interval_analysis": payload.get("interval_analysis", []) if isinstance(payload.get("interval_analysis"), list) else [],
        "melody_contour": payload.get("melody_contour", []) if isinstance(payload.get("melody_contour"), list) else [],
        "harmony_sonority": payload.get("harmony_sonority", []) if isinstance(payload.get("harmony_sonority"), list) else [],
        "chord_movement": payload.get("chord_movement", []) if isinstance(payload.get("chord_movement"), list) else [],
        "counterpoint": payload.get("counterpoint", []) if isinstance(payload.get("counterpoint"), list) else [],
        "tuning_system": payload.get("tuning_system", []) if isinstance(payload.get("tuning_system"), list) else [],
    }


def _build_rhythm_summary(feature_dir: Path) -> dict[str, Any]:
    payload = _safe_json(feature_dir / "rhythm_features.json")
    return {
        "path": (feature_dir / "rhythm_features.json").resolve().as_posix() if (feature_dir / "rhythm_features.json").exists() else None,
        "summary": payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {},
        "records": payload.get("records", []) if isinstance(payload.get("records"), list) else [],
        "rhythm_motifs": payload.get("rhythm_motifs", {}) if isinstance(payload.get("rhythm_motifs"), dict) else {},
        "rhythm_motif_groups": payload.get("rhythm_motif_groups", []) if isinstance(payload.get("rhythm_motif_groups"), list) else [],
    }


def _build_harmony_summary(feature_dir: Path) -> dict[str, Any]:
    payload = _safe_json(feature_dir / "harmony_features.json")
    return {
        "path": (feature_dir / "harmony_features.json").resolve().as_posix() if (feature_dir / "harmony_features.json").exists() else None,
        "summary": payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {},
        "records": payload.get("records", []) if isinstance(payload.get("records"), list) else [],
        "chord_movement_summary": payload.get("chord_movement_summary", {}) if isinstance(payload.get("chord_movement_summary"), dict) else {},
    }


def _build_tag_summary(feature_dir: Path) -> dict[str, Any]:
    payload = _safe_json(feature_dir / "tags.json")
    top = payload.get("top_unique_tags", [])
    tags = [str(item.get("tag")) for item in top[:12] if isinstance(item, dict)]
    return {
        "path": (feature_dir / "tags.json").resolve().as_posix() if (feature_dir / "tags.json").exists() else None,
        "style_tags_weak": tags,
        "all_tags": payload.get("tags", []) if isinstance(payload.get("tags"), list) else [],
    }


def _build_witness_refs(feature_dir: Path) -> tuple[dict[str, str | None], dict[str, str | None], dict[str, Any]]:
    ext = feature_dir / "external_model_features"
    external_witness_refs = {
        "essentia_features": (ext / "essentia_features.json").resolve().as_posix() if (ext / "essentia_features.json").exists() else None,
        "music21_features": (ext / "music21_features.json").resolve().as_posix() if (ext / "music21_features.json").exists() else None,
        "musicnn_features": (ext / "musicnn_features.json").resolve().as_posix() if (ext / "musicnn_features.json").exists() else None,
        "beat_tracker_features": (ext / "beat_tracker_features.json").resolve().as_posix() if (ext / "beat_tracker_features.json").exists() else None,
        "omnizart_availability": (ext / "omnizart_availability.json").resolve().as_posix() if (ext / "omnizart_availability.json").exists() else None,
    }
    consensus_refs = {
        "model_consensus_ref": (ext / "model_consensus.json").resolve().as_posix() if (ext / "model_consensus.json").exists() else None,
        "model_witness_comparison_ref": (ext / "model_witness_comparison.json").resolve().as_posix() if (ext / "model_witness_comparison.json").exists() else None,
    }
    consensus_payload = _safe_json(ext / "model_consensus.json")
    return external_witness_refs, consensus_refs, consensus_payload


def _summarize_notes(events: list[dict[str, float]], duration_seconds: float) -> dict[str, Any]:
    note_count = len(events)
    if note_count == 0:
        return {
            "note_count": 0,
            "duration_seconds": round(duration_seconds, 6),
            "note_density_per_second": 0.0,
            "pitch_range": None,
            "velocity_mean": None,
            "polyphony_proxy": 0.0,
        }
    notes = [int(item["note"]) for item in events]
    vel = [float(item["velocity"]) for item in events]
    density = note_count / max(1e-6, duration_seconds)
    return {
        "note_count": note_count,
        "duration_seconds": round(duration_seconds, 6),
        "note_density_per_second": round(density, 6),
        "pitch_range": {"min_note": min(notes), "max_note": max(notes)},
        "velocity_mean": round(mean(vel), 6),
        "polyphony_proxy": round(_clamp(density / 6.0), 6),
    }


def _tokenize_target(events: list[dict[str, float]], start_seconds: float, end_seconds: float) -> dict[str, Any]:
    clipped = events[:128]
    rhythm_tokens: list[str] = []
    pitch_tokens: list[str] = []
    contour_tokens: list[str] = []
    chord_tokens: list[str] = []
    prev_start = None
    prev_note = None
    pitch_class_counter: Counter[int] = Counter()
    for event in clipped:
        rel_start = max(0.0, event["start"] - start_seconds)
        dur = max(1e-4, event["end"] - event["start"])
        rhythm_tokens.append(f"on_{round(rel_start,3)}_dur_{round(dur,3)}")
        note = int(event["note"])
        pitch_tokens.append(f"n{note}")
        pitch_class_counter[note % 12] += 1
        if prev_start is not None:
            ioi = max(0.0, event["start"] - prev_start)
            rhythm_tokens.append(f"ioi_{round(ioi,3)}")
        if prev_note is not None:
            delta = note - prev_note
            if delta > 0:
                contour_tokens.append("up")
            elif delta < 0:
                contour_tokens.append("down")
            else:
                contour_tokens.append("same")
        prev_start = event["start"]
        prev_note = note
    for pc, _ in pitch_class_counter.most_common(6):
        chord_tokens.append(f"pc{pc}")
    velocities = [float(item["velocity"]) for item in clipped]
    duration = max(1e-6, end_seconds - start_seconds)
    return {
        "midi_events": [
            {
                "start": round(item["start"], 6),
                "end": round(item["end"], 6),
                "note": int(item["note"]),
                "velocity": int(item["velocity"]),
            }
            for item in clipped
        ],
        "piano_roll_summary": {
            "note_count": len(clipped),
            "duration_seconds": round(duration, 6),
            "notes_per_second": round(len(clipped) / duration, 6),
        },
        "note_sequence_summary": {
            "first_notes": [int(item["note"]) for item in clipped[:16]],
            "last_notes": [int(item["note"]) for item in clipped[-16:]],
        },
        "rhythm_tokens": rhythm_tokens[:128],
        "pitch_tokens": pitch_tokens[:128],
        "chord_or_sonority_tokens": chord_tokens[:64],
        "contour_tokens": contour_tokens[:128],
        "velocity_profile": {
            "mean": round(mean(velocities), 6) if velocities else 0.0,
            "max": max(velocities) if velocities else 0.0,
            "min": min(velocities) if velocities else 0.0,
        },
        "timing_deviation_profile": {
            "humanization_proxy": round(_clamp(len(set(rhythm_tokens[:32])) / 32.0), 6),
            "swing_proxy": round(_clamp(sum(1 for token in rhythm_tokens if "ioi_" in token) / max(1, len(rhythm_tokens))), 6),
        },
        "arrangement_density_profile": {
            "density_score": round(_score_density(len(clipped), duration), 6),
            "polyphony_proxy": round(_clamp((len(clipped) / duration) / 7.0), 6),
        },
    }


def _conditioning(
    *,
    content_state: str,
    meter_summary: dict[str, Any],
    pitch_summary: dict[str, Any],
    rhythm_summary: dict[str, Any],
    harmony_summary: dict[str, Any],
    tag_summary: dict[str, Any],
    model_source_refs: list[str],
    theory_source_refs: list[str],
) -> dict[str, Any]:
    macro = pitch_summary.get("macro_record", {})
    return {
        "content_state": content_state,
        "tempo_context": {
            "local_tempo_bpm_median": meter_summary.get("summary", {}).get("local_tempo_bpm_median"),
            "pulse_stability_mean": meter_summary.get("summary", {}).get("pulse_stability_mean"),
            "grid_confidence_mean": meter_summary.get("summary", {}).get("grid_confidence_mean"),
        },
        "meter_hypotheses": meter_summary.get("meter_hypotheses", [])[:3],
        "groove_profile": {
            "subdivision_histogram": meter_summary.get("summary", {}).get("subdivision_histogram", {}),
            "top_rhythm_motifs": rhythm_summary.get("rhythm_motifs", {}).get("motifs", [])[:4]
            if isinstance(rhythm_summary.get("rhythm_motifs"), dict)
            else [],
        },
        "pitch_center_context": {
            "key_hypotheses": macro.get("key_hypotheses", []) if isinstance(macro, dict) else [],
            "pitch_center_strength": macro.get("pitch_center_strength", {}) if isinstance(macro, dict) else {},
        },
        "harmony_context": {
            "chord_movement_summary": harmony_summary.get("chord_movement_summary", {}),
            "recurring_sonority_families": macro.get("recurring_sonority_families", []) if isinstance(macro, dict) else [],
        },
        "interval_profile": {
            "interval_count": len(pitch_summary.get("interval_analysis", [])),
            "counterpoint_count": len(pitch_summary.get("counterpoint", [])),
        },
        "melodic_contour_context": {
            "contour_record_count": len(pitch_summary.get("melody_contour", [])),
        },
        "density_arc_context": {
            "register_density_arc": macro.get("register_density_arc", {}) if isinstance(macro, dict) else {},
        },
        "macro_section_context": {
            "macro_section_candidates": meter_summary.get("summary", {}).get("macro_section_candidates", []),
            "macro_form_candidates": macro.get("macro_form_candidates", []) if isinstance(macro, dict) else [],
        },
        "style_tags_weak": tag_summary.get("style_tags_weak", []),
        "theory_source_refs": theory_source_refs,
        "model_source_refs": model_source_refs,
    }


def _quality_score(
    *,
    task_type: str,
    content_state: str,
    note_count: int,
    duration_seconds: float,
    reliability_score: float,
    route_confidence: float,
    meter_summary: dict[str, Any],
    consensus_payload: dict[str, Any],
    review_heavy: bool,
    motif_strength: float,
) -> dict[str, float]:
    policy = TASK_POLICIES.get(task_type, {})
    allowed_states = policy.get("allowed_content_states", [])
    if "non_silence_any" in allowed_states:
        route_suitability = 0.9 if content_state in NON_SILENCE_STATES else 0.1
    else:
        route_suitability = 1.0 if content_state in allowed_states else (0.25 if content_state in NON_SILENCE_STATES else 0.05)
    phrase_boundary_quality = 0.75
    target_density = _score_density(note_count, duration_seconds)
    musical_completeness = _clamp((note_count / max(1, policy.get("minimum_note_count", 8))) * 0.8 + 0.2, 0.0, 1.0)
    disagreements = consensus_payload.get("disagreements", [])
    if not isinstance(disagreements, list):
        disagreements = []
    unresolved = consensus_payload.get("unresolved_conflicts", [])
    if not isinstance(unresolved, list):
        unresolved = []
    status = str(consensus_payload.get("consensus_status", "missing"))
    witness_agreement_score = 0.5
    if status == "supportive":
        witness_agreement_score = 0.85
    elif status == "conflicted":
        witness_agreement_score = 0.3
    elif status == "missing":
        witness_agreement_score = 0.45
    ambiguity_penalty = 0.0
    ambiguity_penalty += 0.2 if _safe_float(meter_summary.get("ambiguity"), 1.0) > 0.7 else 0.0
    ambiguity_penalty += 0.2 if len(unresolved) > 0 else 0.0
    ambiguity_penalty += 0.15 if len(disagreements) > 0 else 0.0
    review_penalty = 0.25 if review_heavy else 0.0
    weighted = (
        0.18 * _clamp(reliability_score)
        + 0.12 * _clamp(route_suitability)
        + 0.08 * _clamp(phrase_boundary_quality)
        + 0.12 * _clamp(target_density)
        + 0.12 * _clamp(musical_completeness)
        + 0.14 * _clamp(motif_strength)
        + 0.12 * _clamp(witness_agreement_score)
        + 0.12 * _clamp(route_confidence)
    )
    final_score = _clamp(weighted - ambiguity_penalty - review_penalty)
    return {
        "transcription_reliability": round(_clamp(reliability_score), 6),
        "route_suitability": round(_clamp(route_suitability), 6),
        "phrase_boundary_quality": round(_clamp(phrase_boundary_quality), 6),
        "target_density": round(_clamp(target_density), 6),
        "musical_completeness": round(_clamp(musical_completeness), 6),
        "repetition_or_motif_strength": round(_clamp(motif_strength), 6),
        "witness_agreement_score": round(_clamp(witness_agreement_score), 6),
        "ambiguity_penalty": round(_clamp(ambiguity_penalty), 6),
        "review_penalty": round(_clamp(review_penalty), 6),
        "final_score": round(final_score, 6),
    }


def _split_recommendation(final_score: float, content_state: str) -> str:
    if content_state == "silence_or_noise":
        return "exclude"
    if final_score >= 0.72:
        return "train"
    if final_score >= 0.58:
        return "validation"
    if final_score >= 0.35:
        return "review"
    return "exclude"


def _task_allowed(task_type: str, content_state: str) -> bool:
    policy = TASK_POLICIES.get(task_type, {})
    allowed_states = policy.get("allowed_content_states", [])
    if "non_silence_any" in allowed_states:
        return content_state in NON_SILENCE_STATES
    return content_state in allowed_states


def _novelty_potential(
    *,
    task_type: str,
    quality_score: dict[str, float],
    motif_strength: float,
    ambiguity: float,
    content_state: str,
) -> float:
    base = quality_score["final_score"] * 0.5 + motif_strength * 0.3 + _clamp(ambiguity) * 0.2
    if task_type in {"motif_transformation", "reharmonization_candidate", "texture_transfer"}:
        base += 0.08
    if content_state in {"polyphonic_full_mix", "harmonic_dominant"}:
        base += 0.04
    return round(_clamp(base), 6)


def _feature_refs(feature_dir: Path) -> dict[str, str | None]:
    return {
        "rhythm_features": (feature_dir / "rhythm_features.json").resolve().as_posix() if (feature_dir / "rhythm_features.json").exists() else None,
        "harmony_features": (feature_dir / "harmony_features.json").resolve().as_posix() if (feature_dir / "harmony_features.json").exists() else None,
        "meter_time_features": (feature_dir / "rhythm_time" / "meter_time_features.json").resolve().as_posix() if (feature_dir / "rhythm_time" / "meter_time_features.json").exists() else None,
        "pitch_harmony_features": (feature_dir / "pitch_harmony" / "pitch_harmony_features.json").resolve().as_posix() if (feature_dir / "pitch_harmony" / "pitch_harmony_features.json").exists() else None,
        "tags": (feature_dir / "tags.json").resolve().as_posix() if (feature_dir / "tags.json").exists() else None,
        "quality_gates": (feature_dir / "trust" / "quality_gates.json").resolve().as_posix() if (feature_dir / "trust" / "quality_gates.json").exists() else None,
        "transcription_reliability": (feature_dir / "trust" / "transcription_reliability.json").resolve().as_posix() if (feature_dir / "trust" / "transcription_reliability.json").exists() else None,
    }


def build_generative_training_examples(performance_manifest_path: Path) -> tuple[Path, Path, Path]:
    ctx = resolve_performance_context(performance_manifest_path)
    feature_dir = ctx["feature_dir"]
    segments_manifest = load_json(ctx["segments_manifest_path"])
    windows = _segment_windows(segments_manifest)
    segments = _segments(segments_manifest)

    merged_midi_path = ctx["merged_midi_path"] if isinstance(ctx["merged_midi_path"], Path) and ctx["merged_midi_path"] else None
    all_events = _load_note_events(merged_midi_path)
    reliability_by_window = _build_reliability_lookup(feature_dir)
    route_rows, _decisions_by_source, routing_refs = _build_routing_lookup(feature_dir)
    meter_summary = _build_meter_summary(feature_dir)
    pitch_summary = _build_pitch_summary(feature_dir)
    rhythm_summary = _build_rhythm_summary(feature_dir)
    harmony_summary = _build_harmony_summary(feature_dir)
    tag_summary = _build_tag_summary(feature_dir)
    external_witness_refs, consensus_refs, consensus_payload = _build_witness_refs(feature_dir)
    quality_gates = _safe_json(feature_dir / "trust" / "quality_gates.json")
    review_heavy = str(quality_gates.get("overall_quality_status", "")) == "review_required"

    model_source_refs = sorted({str(item.get("provider_id")) for item in MODEL_SOURCES})
    theory_source_refs = sorted({str(item.get("source_id")) for item in THEORY_SOURCES})

    out_dir = resolve_artifact_performance_dir(
        Path("datasets") / "generative_training",
        str(ctx["performance_id"]),
    ) / str(ctx["segment_run_id"])
    out_dir.mkdir(parents=True, exist_ok=True)

    feature_refs = _feature_refs(feature_dir)
    rhythm_time_refs = {"meter_time_features_path": meter_summary.get("path")}
    pitch_harmony_refs = {"pitch_harmony_features_path": pitch_summary.get("path")}

    by_window = {str(w["window_id"]): w for w in windows}
    example_rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    def make_example(
        *,
        task_type: str,
        context_start_seconds: float,
        context_end_seconds: float,
        target_start_seconds: float,
        target_end_seconds: float,
        context_midi_ref: str | None,
        target_midi_ref: str | None,
        motif_strength: float = 0.3,
        context_window_id: str | None = None,
        target_window_id: str | None = None,
        limitations: list[str] | None = None,
    ) -> None:
        start_seconds = min(context_start_seconds, target_start_seconds)
        end_seconds = max(context_end_seconds, target_end_seconds)
        duration_seconds = max(1e-6, target_end_seconds - target_start_seconds)
        content_state, route_confidence = _dominant_content_state(
            start_seconds=target_start_seconds,
            end_seconds=target_end_seconds,
            route_rows=route_rows,
        )
        if not _task_allowed(task_type, content_state):
            return
        target_events = _events_in_range(all_events, target_start_seconds, target_end_seconds)
        context_events = _events_in_range(all_events, context_start_seconds, context_end_seconds)
        note_count = len(target_events)
        policy = TASK_POLICIES.get(task_type, {})
        if note_count < int(policy.get("minimum_note_count", 1)):
            return

        reliability_row = reliability_by_window.get(str(target_window_id or ""), {})
        reliability_score = _safe_float(reliability_row.get("transcription_reliability_score"), 0.65)
        quality_score = _quality_score(
            task_type=task_type,
            content_state=content_state,
            note_count=note_count,
            duration_seconds=duration_seconds,
            reliability_score=reliability_score,
            route_confidence=route_confidence,
            meter_summary=meter_summary,
            consensus_payload=consensus_payload,
            review_heavy=review_heavy,
            motif_strength=motif_strength,
        )
        split = _split_recommendation(quality_score["final_score"], content_state)
        novelty_potential_score = _novelty_potential(
            task_type=task_type,
            quality_score=quality_score,
            motif_strength=motif_strength,
            ambiguity=_safe_float(meter_summary.get("ambiguity"), 0.4),
            content_state=content_state,
        )

        target_representation = _tokenize_target(target_events, target_start_seconds, target_end_seconds)
        input_summary = {
            "context_note_summary": _summarize_notes(context_events, max(1e-6, context_end_seconds - context_start_seconds)),
            "target_note_summary": _summarize_notes(target_events, duration_seconds),
            "context_window_id": context_window_id,
            "target_window_id": target_window_id,
        }
        target_summary = {
            "note_count": note_count,
            "duration_seconds": round(duration_seconds, 6),
            "task_type": task_type,
        }
        conditioning = _conditioning(
            content_state=content_state,
            meter_summary=meter_summary,
            pitch_summary=pitch_summary,
            rhythm_summary=rhythm_summary,
            harmony_summary=harmony_summary,
            tag_summary=tag_summary,
            model_source_refs=model_source_refs,
            theory_source_refs=theory_source_refs,
        )
        example_id = (
            f"{ctx['performance_id']}:{ctx['segment_run_id']}:{task_type}:"
            f"{round(context_start_seconds,3)}-{round(context_end_seconds,3)}:"
            f"{round(target_start_seconds,3)}-{round(target_end_seconds,3)}"
        )
        if example_id in seen_ids:
            return
        seen_ids.add(example_id)
        row = generative_example(
            example_id=example_id,
            performance_id=str(ctx["performance_id"]),
            segment_run_id=str(ctx["segment_run_id"]),
            task_type=task_type,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            context_start_seconds=context_start_seconds,
            context_end_seconds=context_end_seconds,
            target_start_seconds=target_start_seconds,
            target_end_seconds=target_end_seconds,
            audio_ref=str(ctx["performance_manifest"].get("source_path") or ""),
            context_midi_ref=context_midi_ref,
            target_midi_ref=target_midi_ref,
            full_midi_ref=merged_midi_path.resolve().as_posix() if merged_midi_path and merged_midi_path.exists() else None,
            feature_refs=feature_refs,
            rhythm_time_refs=rhythm_time_refs,
            pitch_harmony_refs=pitch_harmony_refs,
            routing_refs=routing_refs,
            external_witness_refs=external_witness_refs,
            consensus_refs=consensus_refs,
            input_summary=input_summary,
            target_summary=target_summary,
            conditioning=conditioning,
            target_representation=target_representation,
            loss_domains=[str(item) for item in policy.get("target_domains", [])],
            trust_policy={
                "preferred_trust_status": policy.get("preferred_trust_status"),
                "weak_label_usage_policy": policy.get("weak_label_usage_policy"),
                "review_policy": policy.get("review_policy"),
                "never_promote_weak_labels_to_ground_truth": True,
            },
            quality_score=quality_score,
            novelty_potential_score=novelty_potential_score,
            limitations=(limitations or [])
            + [f"task_policy={task_type}"]
            + (["split=review_due_to_low_quality"] if split in {"review", "exclude"} else []),
            split_recommendation=split,
        )
        example_rows.append(row)

    # A) Window continuation.
    for i in range(len(windows) - 1):
        current = windows[i]
        nxt = windows[i + 1]
        make_example(
            task_type="continuation",
            context_start_seconds=float(current["start_seconds"]),
            context_end_seconds=float(current["end_seconds"]),
            target_start_seconds=float(nxt["start_seconds"]),
            target_end_seconds=float(nxt["end_seconds"]),
            context_midi_ref=str(current.get("midi_path") or merged_midi_path.as_posix() if merged_midi_path else ""),
            target_midi_ref=str(nxt.get("midi_path") or merged_midi_path.as_posix() if merged_midi_path else ""),
            motif_strength=0.45,
            context_window_id=str(current["window_id"]),
            target_window_id=str(nxt["window_id"]),
        )

    # B) Phrase continuation (adjacent segments).
    for i in range(len(segments) - 1):
        seg = segments[i]
        nxt = segments[i + 1]
        make_example(
            task_type="phrase_continuation",
            context_start_seconds=float(seg["start_seconds"]),
            context_end_seconds=float(seg["end_seconds"]),
            target_start_seconds=float(nxt["start_seconds"]),
            target_end_seconds=float(nxt["end_seconds"]),
            context_midi_ref=merged_midi_path.as_posix() if merged_midi_path else None,
            target_midi_ref=merged_midi_path.as_posix() if merged_midi_path else None,
            motif_strength=0.4,
            limitations=[f"segment_pair={seg['segment_id']}->{nxt['segment_id']}"],
        )

    # C/D/E) Specialized continuation based on content-state.
    for i in range(len(windows) - 1):
        current = windows[i]
        nxt = windows[i + 1]
        target_state, _ = _dominant_content_state(
            start_seconds=float(nxt["start_seconds"]),
            end_seconds=float(nxt["end_seconds"]),
            route_rows=route_rows,
        )
        if target_state in {"rhythm_dominant", "percussive_only", "polyphonic_full_mix"}:
            make_example(
                task_type="groove_continuation",
                context_start_seconds=float(current["start_seconds"]),
                context_end_seconds=float(current["end_seconds"]),
                target_start_seconds=float(nxt["start_seconds"]),
                target_end_seconds=float(nxt["end_seconds"]),
                context_midi_ref=str(current.get("midi_path") or merged_midi_path.as_posix() if merged_midi_path else ""),
                target_midi_ref=str(nxt.get("midi_path") or merged_midi_path.as_posix() if merged_midi_path else ""),
                motif_strength=0.55,
                context_window_id=str(current["window_id"]),
                target_window_id=str(nxt["window_id"]),
            )
        if target_state in {"harmonic_dominant", "polyphonic_full_mix"}:
            make_example(
                task_type="harmony_continuation",
                context_start_seconds=float(current["start_seconds"]),
                context_end_seconds=float(current["end_seconds"]),
                target_start_seconds=float(nxt["start_seconds"]),
                target_end_seconds=float(nxt["end_seconds"]),
                context_midi_ref=str(current.get("midi_path") or merged_midi_path.as_posix() if merged_midi_path else ""),
                target_midi_ref=str(nxt.get("midi_path") or merged_midi_path.as_posix() if merged_midi_path else ""),
                motif_strength=0.52,
                context_window_id=str(current["window_id"]),
                target_window_id=str(nxt["window_id"]),
            )
        if target_state in {"melodic_lead", "vocal_dominant", "rap_vocal_dominant", "polyphonic_full_mix"}:
            make_example(
                task_type="melody_continuation",
                context_start_seconds=float(current["start_seconds"]),
                context_end_seconds=float(current["end_seconds"]),
                target_start_seconds=float(nxt["start_seconds"]),
                target_end_seconds=float(nxt["end_seconds"]),
                context_midi_ref=str(current.get("midi_path") or merged_midi_path.as_posix() if merged_midi_path else ""),
                target_midi_ref=str(nxt.get("midi_path") or merged_midi_path.as_posix() if merged_midi_path else ""),
                motif_strength=0.58,
                context_window_id=str(current["window_id"]),
                target_window_id=str(nxt["window_id"]),
            )

    # F) Call-response from adjacent phrase/segment windows.
    for i in range(len(windows) - 1):
        current = windows[i]
        nxt = windows[i + 1]
        curr_events = _events_in_range(all_events, float(current["start_seconds"]), float(current["end_seconds"]))
        next_events = _events_in_range(all_events, float(nxt["start_seconds"]), float(nxt["end_seconds"]))
        c_count = len(curr_events)
        n_count = len(next_events)
        if c_count < 6 or n_count < 6:
            continue
        ratio = max(c_count, n_count) / max(1, min(c_count, n_count))
        if ratio > 2.5:
            continue
        make_example(
            task_type="call_response",
            context_start_seconds=float(current["start_seconds"]),
            context_end_seconds=float(current["end_seconds"]),
            target_start_seconds=float(nxt["start_seconds"]),
            target_end_seconds=float(nxt["end_seconds"]),
            context_midi_ref=str(current.get("midi_path") or merged_midi_path.as_posix() if merged_midi_path else ""),
            target_midi_ref=str(nxt.get("midi_path") or merged_midi_path.as_posix() if merged_midi_path else ""),
            motif_strength=0.62,
            context_window_id=str(current["window_id"]),
            target_window_id=str(nxt["window_id"]),
        )

    # G) Motif transformation from rhythm motif groups.
    motif_groups = rhythm_summary.get("rhythm_motif_groups", [])
    if isinstance(motif_groups, list):
        region_to_window: dict[str, dict[str, Any]] = {}
        for route in route_rows:
            region_to_window[str(route.get("source_record_id", ""))] = route
            region_to_window[str(route.get("route_id", ""))] = route
        for group in motif_groups:
            if not isinstance(group, dict):
                continue
            region_ids = group.get("region_ids", [])
            if not isinstance(region_ids, list) or len(region_ids) < 2:
                continue
            src = region_to_window.get(str(region_ids[0]))
            tgt = region_to_window.get(str(region_ids[1]))
            if not src or not tgt:
                continue
            make_example(
                task_type="motif_transformation",
                context_start_seconds=_safe_float(src.get("start_seconds"), 0.0),
                context_end_seconds=_safe_float(src.get("end_seconds"), 0.0),
                target_start_seconds=_safe_float(tgt.get("start_seconds"), 0.0),
                target_end_seconds=_safe_float(tgt.get("end_seconds"), 0.0),
                context_midi_ref=merged_midi_path.as_posix() if merged_midi_path else None,
                target_midi_ref=merged_midi_path.as_posix() if merged_midi_path else None,
                motif_strength=_clamp(_safe_float(group.get("rhythm_family_confidence"), 0.5)),
                limitations=[f"motif_group_id={group.get('motif_group_id')}"],
            )

    # H) Section transition.
    for i in range(len(segments) - 1):
        seg = segments[i]
        nxt = segments[i + 1]
        boundary_context_start = max(float(seg["start_seconds"]), float(seg["end_seconds"]) - min(12.0, float(seg["duration_seconds"])))
        boundary_target_end = min(float(nxt["end_seconds"]), float(nxt["start_seconds"]) + min(12.0, float(nxt["duration_seconds"])))
        make_example(
            task_type="section_transition",
            context_start_seconds=boundary_context_start,
            context_end_seconds=float(seg["end_seconds"]),
            target_start_seconds=float(nxt["start_seconds"]),
            target_end_seconds=boundary_target_end,
            context_midi_ref=merged_midi_path.as_posix() if merged_midi_path else None,
            target_midi_ref=merged_midi_path.as_posix() if merged_midi_path else None,
            motif_strength=0.48,
            limitations=[f"section={seg.get('section_label')}->{nxt.get('section_label')}"],
        )

    # I) Buildup to release (density ramp then drop across three windows).
    for i in range(len(windows) - 2):
        w0 = windows[i]
        w1 = windows[i + 1]
        w2 = windows[i + 2]
        c0 = len(_events_in_range(all_events, float(w0["start_seconds"]), float(w0["end_seconds"])))
        c1 = len(_events_in_range(all_events, float(w1["start_seconds"]), float(w1["end_seconds"])))
        c2 = len(_events_in_range(all_events, float(w2["start_seconds"]), float(w2["end_seconds"])))
        if not (c1 > c0 and c2 < c1):
            continue
        make_example(
            task_type="buildup_to_release",
            context_start_seconds=float(w0["start_seconds"]),
            context_end_seconds=float(w1["end_seconds"]),
            target_start_seconds=float(w2["start_seconds"]),
            target_end_seconds=float(w2["end_seconds"]),
            context_midi_ref=merged_midi_path.as_posix() if merged_midi_path else None,
            target_midi_ref=merged_midi_path.as_posix() if merged_midi_path else None,
            motif_strength=0.66,
            context_window_id=str(w1["window_id"]),
            target_window_id=str(w2["window_id"]),
        )

    # J) Infill examples from window triplets.
    for i in range(len(windows) - 2):
        before = windows[i]
        middle = windows[i + 1]
        after = windows[i + 2]
        make_example(
            task_type="infill_missing_region",
            context_start_seconds=float(before["start_seconds"]),
            context_end_seconds=float(after["end_seconds"]),
            target_start_seconds=float(middle["start_seconds"]),
            target_end_seconds=float(middle["end_seconds"]),
            context_midi_ref=merged_midi_path.as_posix() if merged_midi_path else None,
            target_midi_ref=str(middle.get("midi_path") or merged_midi_path.as_posix() if merged_midi_path else ""),
            motif_strength=0.5,
            context_window_id=str(before["window_id"]),
            target_window_id=str(middle["window_id"]),
        )

    split_counts = Counter(str(item.get("split_recommendation", "review")) for item in example_rows)
    task_counts = Counter(str(item.get("task_type", "unknown")) for item in example_rows)
    quality_values = [_safe_float(item.get("quality_score", {}).get("final_score"), 0.0) for item in example_rows]
    avg_quality = round(mean(quality_values), 6) if quality_values else 0.0
    duration_seconds = _safe_float(segments_manifest.get("duration_seconds"), 0.0)
    examples_per_minute = round((len(example_rows) / max(1e-6, duration_seconds)) * 60.0, 6) if duration_seconds > 0 else 0.0
    high_quality_count = sum(1 for item in example_rows if _safe_float(item.get("quality_score", {}).get("final_score"), 0.0) >= 0.72)
    high_quality_examples_per_minute = round((high_quality_count / max(1e-6, duration_seconds)) * 60.0, 6) if duration_seconds > 0 else 0.0
    missing_task_coverage = [task for task in DEFAULT_TASKS if task_counts.get(task, 0) == 0]

    manifest = {
        "performance_id": ctx["performance_id"],
        "segment_run_id": ctx["segment_run_id"],
        "created_at": now_iso(),
        "source_performance_manifest": ctx["performance_manifest_path"].as_posix(),
        "source_feature_dir": feature_dir.as_posix(),
        "source_segments_manifest": ctx["segments_manifest_path"].as_posix(),
        "source_audio_ref": str(ctx["performance_manifest"].get("source_path") or ""),
        "source_merged_midi_ref": merged_midi_path.as_posix() if merged_midi_path else None,
        "generative_examples_count": len(example_rows),
        "split_counts": dict(sorted(split_counts.items())),
        "examples_by_task_type": dict(sorted(task_counts.items())),
        "average_quality_score": avg_quality,
        "examples_per_minute": examples_per_minute,
        "high_quality_examples_per_minute": high_quality_examples_per_minute,
        "high_quality_examples_count": high_quality_count,
        "missing_task_coverage": missing_task_coverage,
        "trust_policy_note": "Weak labels may be used for conditioning only and are never promoted to ground truth.",
    }
    jsonl_path = out_dir / "generative_examples.jsonl"
    manifest_path = out_dir / "generative_manifest.json"
    summary_path = out_dir / "generative_summary.md"
    jsonl_path.write_text(
        "\n".join(json.dumps(item, ensure_ascii=True) for item in example_rows) + ("\n" if example_rows else ""),
        encoding="utf-8",
    )
    save_json(manifest_path, manifest)
    lines = [
        f"# Generative Dataset Summary - {ctx['performance_id']}",
        "",
        f"- segment_run_id: `{ctx['segment_run_id']}`",
        f"- generative_examples_count: `{len(example_rows)}`",
        f"- average_quality_score: `{avg_quality}`",
        f"- examples_per_minute: `{examples_per_minute}`",
        f"- high_quality_examples_per_minute: `{high_quality_examples_per_minute}`",
        f"- missing_task_coverage: `{json.dumps(missing_task_coverage, ensure_ascii=True)}`",
        "",
        "## Examples by task type",
    ]
    if task_counts:
        for task_name, count in sorted(task_counts.items()):
            lines.append(f"- {task_name}: `{count}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Split counts"])
    for split_name, count in sorted(split_counts.items()):
        lines.append(f"- {split_name}: `{count}`")
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return jsonl_path.resolve(), manifest_path.resolve(), summary_path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Build generative music training examples from existing features/artifacts.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    args = parser.parse_args()
    jsonl_path, manifest_path, summary_path = build_generative_training_examples(Path(args.performance_manifest))
    print(f"GENERATIVE_EXAMPLES_JSONL={jsonl_path.as_posix()}")
    print(f"GENERATIVE_MANIFEST_JSON={manifest_path.as_posix()}")
    print(f"GENERATIVE_SUMMARY_MD={summary_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

