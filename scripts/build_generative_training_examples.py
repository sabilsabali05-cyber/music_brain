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
from features.generative.task_policies import (
    CRITICAL_BLOCKERS,
    EVIDENCE_BOOSTERS,
    MAJOR_BLOCKERS,
    SPLIT_THRESHOLDS,
    TASK_POLICIES,
)
from features.model_sources import MODEL_SOURCES
from features.theory_sources import THEORY_SOURCES
from scripts.feature_dataset_common import (
    load_json,
    now_iso,
    resolve_artifact_performance_dir,
    save_json,
)
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


def _path_exists(path_text: Any) -> bool:
    if not isinstance(path_text, str) or not path_text.strip():
        return False
    try:
        return Path(path_text).exists()
    except Exception:  # noqa: BLE001
        return False


def _score_density(note_count: int, duration_seconds: float) -> float:
    if note_count <= 0 or duration_seconds <= 0:
        return 0.0
    density = note_count / max(1e-6, duration_seconds)
    if density < 0.08:
        return 0.1
    if density < 0.25:
        return 0.35
    if density < 1.0:
        return 0.65
    if density < 4.0:
        return 0.85
    return 0.75


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
    for message in merge_tracks(midi.tracks):
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
    rows: list[dict[str, Any]] = []
    for idx, window in enumerate(windows):
        if not isinstance(window, dict):
            continue
        start = _safe_float(window.get("core_start_seconds"), _safe_float(window.get("global_start_seconds"), 0.0))
        end = _safe_float(window.get("core_end_seconds"), _safe_float(window.get("global_end_seconds"), start))
        if end <= start:
            continue
        rows.append(
            {
                "window_id": str(window.get("window_id", f"win_{idx:04d}")),
                "index": int(window.get("index", idx) or idx),
                "start_seconds": start,
                "end_seconds": end,
                "duration_seconds": end - start,
                "midi_path": str(window.get("midi_path") or "").strip() or None,
            }
        )
    return sorted(rows, key=lambda row: (row["start_seconds"], row["end_seconds"]))


def _segments(segments_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    segments = segments_manifest.get("musical_segments", [])
    if not isinstance(segments, list):
        return []
    rows: list[dict[str, Any]] = []
    for idx, segment in enumerate(segments):
        if not isinstance(segment, dict):
            continue
        start = _safe_float(segment.get("global_start_seconds"), 0.0)
        end = _safe_float(segment.get("global_end_seconds"), start)
        if end <= start:
            continue
        rows.append(
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
    return sorted(rows, key=lambda row: (row["start_seconds"], row["end_seconds"]))


def _build_routing_lookup(feature_dir: Path) -> tuple[list[dict[str, Any]], dict[str, str | None]]:
    routing_dir = feature_dir / "routing"
    routes_payload = _safe_json(routing_dir / "content_region_routes.json")
    routes = routes_payload.get("routes", [])
    rows = [row for row in routes if isinstance(row, dict)]
    refs = {
        "content_region_routes": (routing_dir / "content_region_routes.json").resolve().as_posix() if (routing_dir / "content_region_routes.json").exists() else None,
        "analysis_routing_decisions": (routing_dir / "analysis_routing_decisions.json").resolve().as_posix() if (routing_dir / "analysis_routing_decisions.json").exists() else None,
    }
    return rows, refs


def _dominant_content_state(start_seconds: float, end_seconds: float, route_rows: list[dict[str, Any]]) -> tuple[str, float]:
    overlap_by_state: Counter[str] = Counter()
    known_overlap: Counter[str] = Counter()
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
            known_overlap[state] += overlap
        best_conf = max(best_conf, _safe_float(route.get("confidence"), 0.0))
    if not overlap_by_state:
        return "unknown", 0.0
    if known_overlap:
        state, _ = known_overlap.most_common(1)[0]
    else:
        state, _ = overlap_by_state.most_common(1)[0]
    return state, round(best_conf, 6)


def _is_long_form_performance(
    *,
    duration_seconds: float,
    windows_count: int,
    segments_count: int,
    performance_id: str,
    source_name: str,
) -> bool:
    id_text = f"{performance_id} {source_name}".lower()
    long_form_hint = any(token in id_text for token in ("choir", "live", "performance"))
    return duration_seconds >= 600.0 or windows_count >= 24 or segments_count >= 16 or long_form_hint


def _state_compatible(a: str, b: str) -> bool:
    if a == b:
        return True
    if a in {"harmonic_dominant", "polyphonic_full_mix"} and b in {"harmonic_dominant", "polyphonic_full_mix", "melodic_lead"}:
        return True
    if a in {"rhythm_dominant", "percussive_only"} and b in {"rhythm_dominant", "percussive_only", "polyphonic_full_mix"}:
        return True
    if a in {"melodic_lead", "vocal_dominant", "rap_vocal_dominant"} and b in {"melodic_lead", "vocal_dominant", "rap_vocal_dominant", "polyphonic_full_mix"}:
        return True
    return False


def _onset_density(events: list[dict[str, float]], start_seconds: float, end_seconds: float) -> float:
    duration = max(1e-6, end_seconds - start_seconds)
    onsets = sum(1 for event in events if start_seconds <= event["start"] <= end_seconds)
    return onsets / duration


def _overlap_count(records: list[dict[str, Any]], start_seconds: float, end_seconds: float) -> int:
    count = 0
    for record in records:
        if not isinstance(record, dict):
            continue
        r_start = _safe_float(record.get("start_seconds"), 0.0)
        r_end = _safe_float(record.get("end_seconds"), r_start)
        if min(end_seconds, r_end) > max(start_seconds, r_start):
            count += 1
    return count


def _phrase_boundary_evidence(
    *,
    task_type: str,
    context_start_seconds: float,
    context_end_seconds: float,
    target_start_seconds: float,
    target_end_seconds: float,
    context_events: list[dict[str, float]],
    target_events: list[dict[str, float]],
    context_state: str,
    target_state: str,
    segments: list[dict[str, Any]],
    meter_payload: dict[str, Any],
    pitch_payload: dict[str, Any],
    motif_strength: float,
) -> tuple[float, dict[str, float]]:
    context_duration = max(1e-6, context_end_seconds - context_start_seconds)
    target_duration = max(1e-6, target_end_seconds - target_start_seconds)
    density_before = len(context_events) / context_duration
    density_after = len(target_events) / target_duration
    density_change = _clamp(abs(density_after - density_before) / 2.0)
    onset_before = _clamp(_onset_density(context_events, context_start_seconds, context_end_seconds) / 4.0)
    onset_after = _clamp(_onset_density(target_events, target_start_seconds, target_end_seconds) / 4.0)
    onset_balance = _clamp((onset_before + onset_after) * 0.5)

    boundary_distances: list[float] = []
    for segment in segments:
        boundary_distances.append(abs(target_start_seconds - _safe_float(segment.get("start_seconds"), target_start_seconds)))
        boundary_distances.append(abs(target_start_seconds - _safe_float(segment.get("end_seconds"), target_start_seconds)))
    min_boundary_dist = min(boundary_distances) if boundary_distances else 999.0
    segment_boundary_proximity = _clamp(1.0 - min(min_boundary_dist, 8.0) / 8.0)

    routing_state_change = 1.0 if context_state != target_state and target_state != "silence_or_noise" else (0.55 if target_state in NON_SILENCE_STATES else 0.0)

    phrase_refs = meter_payload.get("phrase_rhythm_records", [])
    cycle_refs = meter_payload.get("macro_time_records", [])
    meter_ref_hits = _overlap_count(phrase_refs if isinstance(phrase_refs, list) else [], target_start_seconds, target_end_seconds)
    meter_ref_hits += _overlap_count(cycle_refs if isinstance(cycle_refs, list) else [], target_start_seconds, target_end_seconds)
    meter_phrase_refs = _clamp(meter_ref_hits / 3.0)

    cadence_hits = _overlap_count(
        pitch_payload.get("chord_movement", []) if isinstance(pitch_payload.get("chord_movement"), list) else [],
        target_start_seconds,
        target_end_seconds,
    )
    cadence_hits += _overlap_count(
        pitch_payload.get("harmony_sonority", []) if isinstance(pitch_payload.get("harmony_sonority"), list) else [],
        target_start_seconds,
        target_end_seconds,
    )
    pitch_arrival_refs = _clamp(cadence_hits / 4.0)
    repetition_evidence = _clamp(motif_strength)
    target_duration_adequacy = _clamp(target_duration / max(4.0, _safe_float(TASK_POLICIES.get(task_type, {}).get("minimum_duration"), 4.0)))
    target_density_adequacy = _score_density(len(target_events), target_duration)

    weighted = (
        0.14 * density_change
        + 0.12 * onset_balance
        + 0.12 * segment_boundary_proximity
        + 0.1 * routing_state_change
        + 0.12 * meter_phrase_refs
        + 0.12 * pitch_arrival_refs
        + 0.12 * repetition_evidence
        + 0.08 * target_duration_adequacy
        + 0.08 * target_density_adequacy
    )
    evidence = {
        "density_change_near_boundary": round(density_change, 6),
        "onset_density_balance": round(onset_balance, 6),
        "segment_boundary_proximity": round(segment_boundary_proximity, 6),
        "routing_state_change": round(routing_state_change, 6),
        "meter_phrase_cycle_refs": round(meter_phrase_refs, 6),
        "pitch_harmony_arrival_refs": round(pitch_arrival_refs, 6),
        "repetition_motif_evidence": round(repetition_evidence, 6),
        "target_duration_adequacy": round(target_duration_adequacy, 6),
        "target_density_adequacy": round(target_density_adequacy, 6),
    }
    return round(_clamp(weighted), 6), evidence


def _reliability_lookup(feature_dir: Path) -> dict[str, dict[str, Any]]:
    payload = _safe_json(feature_dir / "trust" / "transcription_reliability.json")
    windows = payload.get("windows", [])
    out: dict[str, dict[str, Any]] = {}
    for row in windows if isinstance(windows, list) else []:
        if isinstance(row, dict):
            out[str(row.get("window_id", ""))] = row
    return out


def _summary_payload(feature_dir: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    rhythm = _safe_json(feature_dir / "rhythm_features.json")
    harmony = _safe_json(feature_dir / "harmony_features.json")
    meter = _safe_json(feature_dir / "rhythm_time" / "meter_time_features.json")
    pitch = _safe_json(feature_dir / "pitch_harmony" / "pitch_harmony_features.json")
    return rhythm, harmony, meter, pitch


def _build_witness_refs(feature_dir: Path) -> tuple[dict[str, str | None], dict[str, str | None], dict[str, Any]]:
    ext = feature_dir / "external_model_features"
    external_refs = {
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
    return external_refs, consensus_refs, _safe_json(ext / "model_consensus.json")


def _feature_refs(feature_dir: Path) -> dict[str, str | None]:
    return {
        "rhythm_features": (feature_dir / "rhythm_features.json").resolve().as_posix() if (feature_dir / "rhythm_features.json").exists() else None,
        "harmony_features": (feature_dir / "harmony_features.json").resolve().as_posix() if (feature_dir / "harmony_features.json").exists() else None,
        "meter_time_features": (feature_dir / "rhythm_time" / "meter_time_features.json").resolve().as_posix() if (feature_dir / "rhythm_time" / "meter_time_features.json").exists() else None,
        "pitch_harmony_features": (feature_dir / "pitch_harmony" / "pitch_harmony_features.json").resolve().as_posix() if (feature_dir / "pitch_harmony" / "pitch_harmony_features.json").exists() else None,
        "tags": (feature_dir / "tags.json").resolve().as_posix() if (feature_dir / "tags.json").exists() else None,
        "transcription_reliability": (feature_dir / "trust" / "transcription_reliability.json").resolve().as_posix() if (feature_dir / "trust" / "transcription_reliability.json").exists() else None,
        "quality_gates": (feature_dir / "trust" / "quality_gates.json").resolve().as_posix() if (feature_dir / "trust" / "quality_gates.json").exists() else None,
    }


def _summarize_notes(events: list[dict[str, float]], duration_seconds: float) -> dict[str, Any]:
    if not events:
        return {
            "note_count": 0,
            "duration_seconds": round(duration_seconds, 6),
            "note_density_per_second": 0.0,
            "pitch_range": None,
        }
    notes = [int(item["note"]) for item in events]
    density = len(events) / max(1e-6, duration_seconds)
    return {
        "note_count": len(events),
        "duration_seconds": round(duration_seconds, 6),
        "note_density_per_second": round(density, 6),
        "pitch_range": {"min_note": min(notes), "max_note": max(notes)},
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
            rhythm_tokens.append(f"ioi_{round(max(0.0, event['start'] - prev_start),3)}")
        if prev_note is not None:
            contour_tokens.append("up" if note > prev_note else "down" if note < prev_note else "same")
        prev_start = event["start"]
        prev_note = note
    for pc, _ in pitch_class_counter.most_common(6):
        chord_tokens.append(f"pc{pc}")
    duration = max(1e-6, end_seconds - start_seconds)
    velocities = [float(item["velocity"]) for item in clipped]
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


def _task_allowed(
    task_type: str,
    content_state: str,
    *,
    has_harmony_evidence: bool = False,
    has_melody_evidence: bool = False,
    has_response_evidence: bool = False,
) -> bool:
    policy = TASK_POLICIES.get(task_type, {})
    allowed = policy.get("allowed_content_states", [])
    if task_type == "harmony_continuation" and has_harmony_evidence:
        return True
    if task_type == "melody_continuation" and has_melody_evidence and content_state in NON_SILENCE_STATES:
        return True
    if task_type == "call_response" and has_response_evidence and content_state in NON_SILENCE_STATES:
        return True
    if "non_silence_any" in allowed:
        return content_state in NON_SILENCE_STATES
    return content_state in allowed


def _quality_components(
    *,
    task_type: str,
    content_state: str,
    note_count: int,
    duration_seconds: float,
    reliability_score: float,
    route_confidence: float,
    meter_ambiguity: float,
    consensus_payload: dict[str, Any],
    review_heavy: bool,
    motif_strength: float,
    phrase_boundary_quality: float,
    phrase_boundary_evidence: float,
    has_meter_ref: bool,
    has_pitch_ref: bool,
    is_long_form: bool,
) -> dict[str, float]:
    policy = TASK_POLICIES.get(task_type, {})
    allowed = policy.get("allowed_content_states", [])
    if "non_silence_any" in allowed:
        route_suitability = 0.92 if content_state in NON_SILENCE_STATES else 0.05
    else:
        route_suitability = 1.0 if content_state in allowed else (0.25 if content_state in NON_SILENCE_STATES else 0.05)

    density_score = _score_density(note_count, duration_seconds)
    completeness = _clamp((note_count / max(1, int(policy.get("minimum_note_count", 4)))) * 0.8 + 0.2)
    if has_meter_ref:
        completeness = _clamp(completeness + 0.04)
    if has_pitch_ref:
        completeness = _clamp(completeness + 0.04)

    consensus_status = str(consensus_payload.get("consensus_status", "missing"))
    disagreements = consensus_payload.get("disagreements", [])
    unresolved = consensus_payload.get("unresolved_conflicts", [])
    if not isinstance(disagreements, list):
        disagreements = []
    if not isinstance(unresolved, list):
        unresolved = []
    if consensus_status == "supportive":
        witness = 0.84
    elif consensus_status == "conflicted":
        witness = 0.42
    else:
        witness = 0.58

    ambiguity_penalty = 0.0
    if meter_ambiguity > 0.72:
        ambiguity_penalty += 0.1
    if disagreements:
        ambiguity_penalty += 0.08
    if unresolved:
        ambiguity_penalty += 0.06
    review_penalty = 0.06 if review_heavy else 0.0

    weighted_pre_penalty = (
        0.24 * _clamp(reliability_score)
        + 0.14 * _clamp(route_suitability)
        + 0.06 * _clamp(phrase_boundary_quality)
        + 0.08 * _clamp(phrase_boundary_evidence)
        + 0.14 * _clamp(density_score)
        + 0.14 * _clamp(completeness)
        + 0.1 * _clamp(motif_strength)
        + 0.14 * _clamp(witness)
    )
    if is_long_form and task_type in {"continuation", "phrase_continuation", "call_response", "buildup_to_release"}:
        weighted_pre_penalty += 0.06
    final_score = _clamp(weighted_pre_penalty - ambiguity_penalty - review_penalty)
    return {
        "transcription_reliability": round(_clamp(reliability_score), 6),
        "route_suitability": round(_clamp(route_suitability), 6),
        "phrase_boundary_quality": round(_clamp(phrase_boundary_quality), 6),
        "phrase_boundary_evidence": round(_clamp(phrase_boundary_evidence), 6),
        "target_density": round(_clamp(density_score), 6),
        "musical_completeness": round(_clamp(completeness), 6),
        "repetition_or_motif_strength": round(_clamp(motif_strength), 6),
        "witness_agreement_score": round(_clamp(witness), 6),
        "ambiguity_penalty": round(_clamp(ambiguity_penalty), 6),
        "review_penalty": round(_clamp(review_penalty), 6),
        "weighted_pre_penalty": round(_clamp(weighted_pre_penalty), 6),
        "final_score": round(final_score, 6),
    }


def _novelty_potential(task_type: str, quality_components: dict[str, float], motif_strength: float, content_state: str) -> float:
    value = (
        0.45 * _safe_float(quality_components.get("final_score"), 0.0)
        + 0.35 * _clamp(motif_strength)
        + 0.2 * _safe_float(quality_components.get("target_density"), 0.0)
    )
    if task_type in {"motif_transformation", "reharmonization_candidate", "texture_transfer"}:
        value += 0.06
    if content_state in {"polyphonic_full_mix", "harmonic_dominant"}:
        value += 0.03
    return round(_clamp(value), 6)


def _split_decision(
    *,
    final_score: float,
    split_reason_codes: list[str],
    failed_policy_checks: list[str],
    critical_blockers: list[str],
) -> str:
    split_reason_codes.extend(critical_blockers)
    split_reason_codes.extend(failed_policy_checks)
    if critical_blockers:
        split_reason_codes.append("critical_blocker")
        split_reason_codes.append("quality_below_threshold")
        return "exclude"

    major_failed = any(code in MAJOR_BLOCKERS for code in failed_policy_checks)
    if final_score >= SPLIT_THRESHOLDS["train"] and not major_failed:
        split_reason_codes.append("quality_meets_train_threshold")
        return "train"
    if final_score >= SPLIT_THRESHOLDS["validation"] and not major_failed:
        split_reason_codes.append("quality_meets_validation_threshold")
        return "validation"
    if final_score >= SPLIT_THRESHOLDS["review"]:
        split_reason_codes.append("quality_below_threshold")
        return "review"
    split_reason_codes.append("quality_below_threshold")
    return "exclude"


def build_generative_training_examples(performance_manifest_path: Path) -> tuple[Path, Path, Path]:
    ctx = resolve_performance_context(performance_manifest_path)
    feature_dir = ctx["feature_dir"]
    segments_manifest = load_json(ctx["segments_manifest_path"])
    windows = _segment_windows(segments_manifest)
    windows_by_id = {str(item["window_id"]): item for item in windows}
    segments = _segments(segments_manifest)
    duration_seconds_manifest = _safe_float(segments_manifest.get("duration_seconds"), 0.0)

    merged_midi_path = ctx["merged_midi_path"] if isinstance(ctx["merged_midi_path"], Path) and ctx["merged_midi_path"] else None
    all_events = _load_note_events(merged_midi_path)
    reliability_lookup = _reliability_lookup(feature_dir)
    route_rows, routing_refs = _build_routing_lookup(feature_dir)
    rhythm_payload, harmony_payload, meter_payload, pitch_payload = _summary_payload(feature_dir)
    feature_refs = _feature_refs(feature_dir)
    rhythm_time_refs = {"meter_time_features_path": feature_refs.get("meter_time_features")}
    pitch_harmony_refs = {"pitch_harmony_features_path": feature_refs.get("pitch_harmony_features")}
    external_witness_refs, consensus_refs, consensus_payload = _build_witness_refs(feature_dir)
    quality_gates = _safe_json(feature_dir / "trust" / "quality_gates.json")
    review_heavy = str(quality_gates.get("overall_quality_status", "")) == "review_required"

    model_source_refs = sorted({str(item.get("provider_id")) for item in MODEL_SOURCES})
    theory_source_refs = sorted({str(item.get("source_id")) for item in THEORY_SOURCES})
    style_tags = [
        str(item.get("tag"))
        for item in (tag for tag in _safe_json(feature_dir / "tags.json").get("top_unique_tags", []) if isinstance(tag, dict))
    ][:12]
    is_long_form = _is_long_form_performance(
        duration_seconds=duration_seconds_manifest,
        windows_count=len(windows),
        segments_count=len(segments),
        performance_id=str(ctx["performance_id"]),
        source_name=str(ctx["performance_manifest"].get("source_name") or ctx["performance_manifest"].get("source_path") or ""),
    )

    out_dir = resolve_artifact_performance_dir(Path("datasets") / "generative_training", str(ctx["performance_id"])) / str(ctx["segment_run_id"])
    out_dir.mkdir(parents=True, exist_ok=True)

    examples: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    extraction_stats: Counter[str] = Counter()
    exclusion_stats: Counter[str] = Counter()
    review_stats: Counter[str] = Counter()

    def make_example(
        *,
        task_type: str,
        context_start_seconds: float,
        context_end_seconds: float,
        target_start_seconds: float,
        target_end_seconds: float,
        context_midi_ref: str | None,
        target_midi_ref: str | None,
        context_window_id: str | None = None,
        target_window_id: str | None = None,
        motif_strength: float = 0.4,
        extraction_notes: list[str] | None = None,
        force_harmony_allow: bool = False,
    ) -> None:
        start_seconds = min(context_start_seconds, target_start_seconds)
        end_seconds = max(context_end_seconds, target_end_seconds)
        example_id = (
            f"{ctx['performance_id']}:{ctx['segment_run_id']}:{task_type}:"
            f"{round(context_start_seconds,3)}-{round(context_end_seconds,3)}:"
            f"{round(target_start_seconds,3)}-{round(target_end_seconds,3)}"
        )
        if example_id in seen_ids:
            return
        seen_ids.add(example_id)

        split_reason_codes: list[str] = []
        failed_policy_checks: list[str] = []
        missing_refs: list[str] = []
        critical_blockers: list[str] = []

        if target_end_seconds <= target_start_seconds:
            critical_blockers.append("missing_target_range")
        if context_end_seconds <= context_start_seconds:
            critical_blockers.append("invalid_timing")

        content_state, route_conf = _dominant_content_state(target_start_seconds, target_end_seconds, route_rows)
        context_state, _ = _dominant_content_state(context_start_seconds, context_end_seconds, route_rows)
        if content_state == "silence_or_noise":
            critical_blockers.append("silence_or_noise_target")

        has_harmony_evidence = bool(
            isinstance(harmony_payload.get("records"), list)
            and any(
                isinstance(row, dict)
                and _safe_float(row.get("start_seconds"), target_start_seconds) <= target_end_seconds
                and _safe_float(row.get("end_seconds"), target_end_seconds) >= target_start_seconds
                for row in harmony_payload.get("records", [])
            )
        ) or bool(
            isinstance(pitch_payload.get("harmony_sonority"), list)
            and any(
                isinstance(row, dict)
                and _safe_float(row.get("start_seconds"), target_start_seconds) <= target_end_seconds
                and _safe_float(row.get("end_seconds"), target_end_seconds) >= target_start_seconds
                for row in pitch_payload.get("harmony_sonority", [])
            )
        )
        has_melody_evidence = bool(
            isinstance(pitch_payload.get("melody_contour"), list)
            and _overlap_count(pitch_payload.get("melody_contour", []), target_start_seconds, target_end_seconds) > 0
        )
        has_response_evidence = has_melody_evidence or has_harmony_evidence
        if not _task_allowed(
            task_type,
            content_state,
            has_harmony_evidence=force_harmony_allow or has_harmony_evidence,
            has_melody_evidence=has_melody_evidence,
            has_response_evidence=has_response_evidence,
        ):
            failed_policy_checks.append("task_policy_failed")
            split_reason_codes.append("route_state_unsuitable")

        policy = TASK_POLICIES.get(task_type, {})
        min_dur = _safe_float(policy.get("minimum_duration"), 0.0)
        max_dur = _safe_float(policy.get("maximum_duration"), 10_000.0)
        duration_seconds = max(1e-6, target_end_seconds - target_start_seconds)
        if duration_seconds < min_dur or duration_seconds > max_dur:
            failed_policy_checks.append("duration_out_of_range")
            split_reason_codes.append("task_policy_failed")

        context_events = _events_in_range(all_events, context_start_seconds, context_end_seconds)
        target_events = _events_in_range(all_events, target_start_seconds, target_end_seconds)
        note_count = len(target_events)
        context_note_count = len(context_events)
        if note_count == 0:
            critical_blockers.append("no_target_events")
        if note_count < int(policy.get("minimum_note_count", 1)):
            failed_policy_checks.append("target_too_sparse")
            split_reason_codes.append("target_too_sparse")

        if not context_midi_ref:
            missing_refs.append("missing_context_midi_ref")
        elif not _path_exists(context_midi_ref):
            missing_refs.append("missing_context_midi_ref")
        if not target_midi_ref:
            critical_blockers.append("missing_target_midi_ref")
        elif not _path_exists(target_midi_ref):
            critical_blockers.append("missing_target_midi_ref")

        if not _path_exists(feature_refs.get("meter_time_features")):
            missing_refs.append("missing_meter_time_refs")
        if not _path_exists(feature_refs.get("pitch_harmony_features")):
            missing_refs.append("missing_pitch_harmony_refs")
        if not any(value for value in external_witness_refs.values()):
            split_reason_codes.append("missing_external_witness_refs")

        reliability_row = reliability_lookup.get(str(target_window_id or ""), {})
        reliability_score = _safe_float(reliability_row.get("transcription_reliability_score"), 0.65)
        if reliability_score < 0.45:
            split_reason_codes.append("low_transcription_reliability")
        phrase_gap = abs(target_start_seconds - context_end_seconds)
        phrase_boundary_quality = _clamp(1.0 - min(1.0, phrase_gap / (4.5 if is_long_form else 3.0)))
        phrase_boundary_evidence, phrase_evidence_components = _phrase_boundary_evidence(
            task_type=task_type,
            context_start_seconds=context_start_seconds,
            context_end_seconds=context_end_seconds,
            target_start_seconds=target_start_seconds,
            target_end_seconds=target_end_seconds,
            context_events=context_events,
            target_events=target_events,
            context_state=context_state,
            target_state=content_state,
            segments=segments,
            meter_payload=meter_payload,
            pitch_payload=pitch_payload,
            motif_strength=motif_strength,
        )
        phrase_boundary_quality = round(_clamp(0.45 * phrase_boundary_quality + 0.55 * phrase_boundary_evidence), 6)
        if phrase_boundary_quality < 0.45:
            split_reason_codes.append("phrase_boundary_weak")

        quality_components = _quality_components(
            task_type=task_type,
            content_state=content_state,
            note_count=note_count,
            duration_seconds=duration_seconds,
            reliability_score=reliability_score,
            route_confidence=route_conf,
            meter_ambiguity=_safe_float(meter_payload.get("ambiguity"), 0.5),
            consensus_payload=consensus_payload,
            review_heavy=review_heavy,
            motif_strength=motif_strength,
            phrase_boundary_quality=phrase_boundary_quality,
            phrase_boundary_evidence=phrase_boundary_evidence,
            has_meter_ref=_path_exists(feature_refs.get("meter_time_features")),
            has_pitch_ref=_path_exists(feature_refs.get("pitch_harmony_features")),
            is_long_form=is_long_form,
        )

        if reliability_score < 0.45:
            failed_policy_checks.append("low_transcription_reliability")
        if quality_components["musical_completeness"] < 0.4:
            split_reason_codes.append("low_musical_completeness")
        if motif_strength < 0.35:
            split_reason_codes.append("weak_or_missing_task_evidence")
        if review_heavy:
            split_reason_codes.append("too_much_review_required")
        if missing_refs:
            split_reason_codes.extend(missing_refs)

        split = _split_decision(
            final_score=quality_components["final_score"],
            split_reason_codes=split_reason_codes,
            failed_policy_checks=failed_policy_checks,
            critical_blockers=critical_blockers,
        )
        if split == "exclude":
            for code in split_reason_codes:
                exclusion_stats[code] += 1
        if split == "review":
            for code in split_reason_codes:
                review_stats[code] += 1

        input_summary = {
            "context_note_summary": _summarize_notes(context_events, max(1e-6, context_end_seconds - context_start_seconds)),
            "target_note_summary": _summarize_notes(target_events, duration_seconds),
            "context_window_id": context_window_id,
            "target_window_id": target_window_id,
        }
        target_summary = {
            "task_type": task_type,
            "note_count": note_count,
            "context_note_count": context_note_count,
            "duration_seconds": round(duration_seconds, 6),
        }
        conditioning = {
            "content_state": content_state,
            "tempo_context": {
                "local_tempo_bpm_median": meter_payload.get("summary", {}).get("local_tempo_bpm_median")
                if isinstance(meter_payload.get("summary"), dict)
                else None,
                "pulse_stability_mean": meter_payload.get("summary", {}).get("pulse_stability_mean")
                if isinstance(meter_payload.get("summary"), dict)
                else None,
            },
            "meter_hypotheses": meter_payload.get("beat_meter_hypotheses", [])[:3]
            if isinstance(meter_payload.get("beat_meter_hypotheses"), list)
            else [],
            "groove_profile": {
                "subdivision_histogram": meter_payload.get("summary", {}).get("subdivision_histogram", {})
                if isinstance(meter_payload.get("summary"), dict)
                else {},
            },
            "pitch_center_context": {
                "key_hypotheses": pitch_payload.get("macro_record", {}).get("key_hypotheses", [])
                if isinstance(pitch_payload.get("macro_record"), dict)
                else [],
            },
            "harmony_context": {
                "chord_movement_summary": harmony_payload.get("chord_movement_summary", {})
                if isinstance(harmony_payload.get("chord_movement_summary"), dict)
                else {},
            },
            "interval_profile": {
                "interval_record_count": len(pitch_payload.get("interval_analysis", []))
                if isinstance(pitch_payload.get("interval_analysis"), list)
                else 0,
            },
            "melodic_contour_context": {
                "contour_record_count": len(pitch_payload.get("melody_contour", []))
                if isinstance(pitch_payload.get("melody_contour"), list)
                else 0,
            },
            "density_arc_context": {
                "register_density_arc": pitch_payload.get("macro_record", {}).get("register_density_arc", {})
                if isinstance(pitch_payload.get("macro_record"), dict)
                else {},
            },
            "macro_section_context": {
                "macro_section_candidates": meter_payload.get("summary", {}).get("macro_section_candidates", [])
                if isinstance(meter_payload.get("summary"), dict)
                else [],
            },
            "style_tags_weak": style_tags,
            "theory_source_refs": theory_source_refs,
            "model_source_refs": model_source_refs,
        }
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
            target_representation=_tokenize_target(target_events, target_start_seconds, target_end_seconds),
            loss_domains=[str(item) for item in policy.get("target_domains", [])],
            trust_policy={
                "preferred_trust_status": policy.get("preferred_trust_status"),
                "weak_label_usage_policy": policy.get("weak_label_usage_policy"),
                "review_policy": policy.get("review_policy"),
                "never_promote_weak_labels_to_ground_truth": True,
            },
            quality_score={k: quality_components[k] for k in (
                "transcription_reliability",
                "route_suitability",
                "phrase_boundary_quality",
                "target_density",
                "musical_completeness",
                "repetition_or_motif_strength",
                "witness_agreement_score",
                "ambiguity_penalty",
                "review_penalty",
                "final_score",
            )},
            novelty_potential_score=_novelty_potential(task_type, quality_components, motif_strength, content_state),
            limitations=(extraction_notes or []) + [f"task_policy={task_type}"],
            split_recommendation=split,
        )
        row["split_reason_codes"] = sorted(set(split_reason_codes))
        row["failed_policy_checks"] = sorted(set(failed_policy_checks))
        row["missing_refs"] = sorted(set(missing_refs))
        row["quality_component_breakdown"] = {
            key: quality_components[key]
            for key in (
                "transcription_reliability",
                "route_suitability",
                "phrase_boundary_quality",
                "phrase_boundary_evidence",
                "target_density",
                "musical_completeness",
                "repetition_or_motif_strength",
                "witness_agreement_score",
                "ambiguity_penalty",
                "review_penalty",
                "weighted_pre_penalty",
                "final_score",
            )
        }
        row["quality_component_breakdown"]["phrase_boundary_evidence_components"] = phrase_evidence_components
        examples.append(row)
        extraction_stats[task_type] += 1

    # A. Window continuation (with long-form compatible pairing).
    for i in range(len(windows) - 1):
        curr = windows[i]
        nxt = windows[i + 1]
        curr_state, _ = _dominant_content_state(float(curr["start_seconds"]), float(curr["end_seconds"]), route_rows)
        nxt_state, _ = _dominant_content_state(float(nxt["start_seconds"]), float(nxt["end_seconds"]), route_rows)
        if nxt_state == "silence_or_noise":
            continue
        if not _state_compatible(curr_state, nxt_state):
            continue
        context_start = float(curr["start_seconds"])
        context_end = float(curr["end_seconds"])
        context_window_id = str(curr["window_id"])
        extraction_notes = ["compatible_state_pairing"]
        if is_long_form and i >= 1:
            prev = windows[i - 1]
            prev_state, _ = _dominant_content_state(float(prev["start_seconds"]), float(prev["end_seconds"]), route_rows)
            if _state_compatible(prev_state, curr_state):
                context_start = float(prev["start_seconds"])
                context_window_id = f"{prev['window_id']}+{curr['window_id']}"
                extraction_notes.append("long_form_two_window_context")
        make_example(
            task_type="continuation",
            context_start_seconds=context_start,
            context_end_seconds=context_end,
            target_start_seconds=float(nxt["start_seconds"]),
            target_end_seconds=float(nxt["end_seconds"]),
            context_midi_ref=str(curr.get("midi_path") or merged_midi_path.as_posix() if merged_midi_path else ""),
            target_midi_ref=str(nxt.get("midi_path") or merged_midi_path.as_posix() if merged_midi_path else ""),
            motif_strength=0.48 if not is_long_form else 0.54,
            context_window_id=context_window_id,
            target_window_id=str(nxt["window_id"]),
            extraction_notes=extraction_notes,
        )

    # B. Phrase continuation.
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
            motif_strength=0.46,
            extraction_notes=[f"segment_pair={seg['segment_id']}->{nxt['segment_id']}"],
        )
    if is_long_form and len(windows) >= 6:
        for i in range(1, len(windows) - 1):
            before = windows[i - 1]
            middle = windows[i]
            after = windows[i + 1]
            b_events = _events_in_range(all_events, float(before["start_seconds"]), float(before["end_seconds"]))
            m_events = _events_in_range(all_events, float(middle["start_seconds"]), float(middle["end_seconds"]))
            a_events = _events_in_range(all_events, float(after["start_seconds"]), float(after["end_seconds"]))
            d_before = len(b_events) / max(1e-6, float(before["duration_seconds"]))
            d_middle = len(m_events) / max(1e-6, float(middle["duration_seconds"]))
            d_after = len(a_events) / max(1e-6, float(after["duration_seconds"]))
            phrase_like = abs(d_after - d_middle) > 0.35 or abs(d_middle - d_before) > 0.35
            if not phrase_like:
                continue
            make_example(
                task_type="phrase_continuation",
                context_start_seconds=float(before["start_seconds"]),
                context_end_seconds=float(middle["end_seconds"]),
                target_start_seconds=float(after["start_seconds"]),
                target_end_seconds=float(after["end_seconds"]),
                context_midi_ref=merged_midi_path.as_posix() if merged_midi_path else None,
                target_midi_ref=merged_midi_path.as_posix() if merged_midi_path else None,
                motif_strength=0.52,
                context_window_id=f"{before['window_id']}+{middle['window_id']}",
                target_window_id=str(after["window_id"]),
                extraction_notes=["phrase_like_internal_boundary", "density_boundary_change"],
            )

    # C/D/E. Task-specific continuation.
    for i in range(len(windows) - 1):
        curr = windows[i]
        nxt = windows[i + 1]
        target_state, _ = _dominant_content_state(float(nxt["start_seconds"]), float(nxt["end_seconds"]), route_rows)
        target_start = float(nxt["start_seconds"])
        target_end = float(nxt["end_seconds"])
        harmony_overlap = any(
            isinstance(row, dict)
            and _safe_float(row.get("start_seconds"), target_start) <= target_end
            and _safe_float(row.get("end_seconds"), target_end) >= target_start
            for row in pitch_payload.get("harmony_sonority", [])
        ) or any(
            isinstance(row, dict)
            and _safe_float(row.get("start_seconds"), target_start) <= target_end
            and _safe_float(row.get("end_seconds"), target_end) >= target_start
            for row in pitch_payload.get("chord_movement", [])
        )
        if target_state in {"rhythm_dominant", "percussive_only", "polyphonic_full_mix"}:
            make_example(
                task_type="groove_continuation",
                context_start_seconds=float(curr["start_seconds"]),
                context_end_seconds=float(curr["end_seconds"]),
                target_start_seconds=float(nxt["start_seconds"]),
                target_end_seconds=float(nxt["end_seconds"]),
                context_midi_ref=str(curr.get("midi_path") or merged_midi_path.as_posix() if merged_midi_path else ""),
                target_midi_ref=str(nxt.get("midi_path") or merged_midi_path.as_posix() if merged_midi_path else ""),
                motif_strength=0.56,
                context_window_id=str(curr["window_id"]),
                target_window_id=str(nxt["window_id"]),
            )
        if target_state in {"harmonic_dominant", "polyphonic_full_mix"} or harmony_overlap:
            make_example(
                task_type="harmony_continuation",
                context_start_seconds=float(curr["start_seconds"]),
                context_end_seconds=float(curr["end_seconds"]),
                target_start_seconds=float(nxt["start_seconds"]),
                target_end_seconds=float(nxt["end_seconds"]),
                context_midi_ref=str(curr.get("midi_path") or merged_midi_path.as_posix() if merged_midi_path else ""),
                target_midi_ref=str(nxt.get("midi_path") or merged_midi_path.as_posix() if merged_midi_path else ""),
                motif_strength=0.6,
                context_window_id=str(curr["window_id"]),
                target_window_id=str(nxt["window_id"]),
                force_harmony_allow=True,
                extraction_notes=["harmony_evidence_overlap" if harmony_overlap else "harmony_state_overlap"],
            )
        if target_state in {"melodic_lead", "vocal_dominant", "rap_vocal_dominant", "polyphonic_full_mix"}:
            make_example(
                task_type="melody_continuation",
                context_start_seconds=float(curr["start_seconds"]),
                context_end_seconds=float(curr["end_seconds"]),
                target_start_seconds=float(nxt["start_seconds"]),
                target_end_seconds=float(nxt["end_seconds"]),
                context_midi_ref=str(curr.get("midi_path") or merged_midi_path.as_posix() if merged_midi_path else ""),
                target_midi_ref=str(nxt.get("midi_path") or merged_midi_path.as_posix() if merged_midi_path else ""),
                motif_strength=0.58,
                context_window_id=str(curr["window_id"]),
                target_window_id=str(nxt["window_id"]),
            )

    # F. Call-response.
    for i in range(len(windows) - 1):
        curr = windows[i]
        nxt = windows[i + 1]
        curr_events = _events_in_range(all_events, float(curr["start_seconds"]), float(curr["end_seconds"]))
        next_events = _events_in_range(all_events, float(nxt["start_seconds"]), float(nxt["end_seconds"]))
        if len(curr_events) < 4 or len(next_events) < 4:
            continue
        ratio = max(len(curr_events), len(next_events)) / max(1, min(len(curr_events), len(next_events)))
        if ratio > 3.5:
            continue
        density_curr = len(curr_events) / max(1e-6, float(curr["duration_seconds"]))
        density_next = len(next_events) / max(1e-6, float(nxt["duration_seconds"]))
        density_contrast = _clamp(abs(density_next - density_curr) / 2.0)
        make_example(
            task_type="call_response",
            context_start_seconds=float(curr["start_seconds"]),
            context_end_seconds=float(curr["end_seconds"]),
            target_start_seconds=float(nxt["start_seconds"]),
            target_end_seconds=float(nxt["end_seconds"]),
            context_midi_ref=str(curr.get("midi_path") or merged_midi_path.as_posix() if merged_midi_path else ""),
            target_midi_ref=str(nxt.get("midi_path") or merged_midi_path.as_posix() if merged_midi_path else ""),
            motif_strength=0.58 + 0.2 * density_contrast,
            context_window_id=str(curr["window_id"]),
            target_window_id=str(nxt["window_id"]),
            extraction_notes=["density_arc_response", "no_hard_vocal_label_requirement"],
        )

    # G. Motif transformation using motif groups -> window ids.
    motif_groups = rhythm_payload.get("rhythm_motif_groups", [])
    motif_generated = 0
    if isinstance(motif_groups, list):
        for group in motif_groups:
            if not isinstance(group, dict):
                continue
            window_ids = [str(item) for item in group.get("window_ids", []) if isinstance(item, str)]
            if len(window_ids) < 2:
                continue
            src_window = windows_by_id.get(window_ids[0])
            tgt_window = None
            for win_id in window_ids[1:]:
                if win_id in windows_by_id:
                    tgt_window = windows_by_id[win_id]
                    break
            if not src_window or not tgt_window:
                continue
            make_example(
                task_type="motif_transformation",
                context_start_seconds=float(src_window["start_seconds"]),
                context_end_seconds=float(src_window["end_seconds"]),
                target_start_seconds=float(tgt_window["start_seconds"]),
                target_end_seconds=float(tgt_window["end_seconds"]),
                context_midi_ref=str(src_window.get("midi_path") or merged_midi_path.as_posix() if merged_midi_path else ""),
                target_midi_ref=str(tgt_window.get("midi_path") or merged_midi_path.as_posix() if merged_midi_path else ""),
                motif_strength=_clamp(_safe_float(group.get("rhythm_family_confidence"), 0.5)),
                context_window_id=str(src_window["window_id"]),
                target_window_id=str(tgt_window["window_id"]),
                extraction_notes=[f"motif_group_id={group.get('motif_group_id')}"],
            )
            motif_generated += 1
            if motif_generated >= 64:
                break

    # H. Section transition.
    for i in range(len(segments) - 1):
        seg = segments[i]
        nxt = segments[i + 1]
        context_start = max(float(seg["start_seconds"]), float(seg["end_seconds"]) - min(12.0, float(seg["duration_seconds"])))
        target_end = min(float(nxt["end_seconds"]), float(nxt["start_seconds"]) + min(12.0, float(nxt["duration_seconds"])))
        make_example(
            task_type="section_transition",
            context_start_seconds=context_start,
            context_end_seconds=float(seg["end_seconds"]),
            target_start_seconds=float(nxt["start_seconds"]),
            target_end_seconds=target_end,
            context_midi_ref=merged_midi_path.as_posix() if merged_midi_path else None,
            target_midi_ref=merged_midi_path.as_posix() if merged_midi_path else None,
            motif_strength=0.5,
            extraction_notes=[f"section={seg.get('section_label')}->{nxt.get('section_label')}"],
        )

    # I. Buildup -> release.
    for i in range(len(windows) - 2):
        w0 = windows[i]
        w1 = windows[i + 1]
        w2 = windows[i + 2]
        c0 = len(_events_in_range(all_events, float(w0["start_seconds"]), float(w0["end_seconds"])))
        c1 = len(_events_in_range(all_events, float(w1["start_seconds"]), float(w1["end_seconds"])))
        c2 = len(_events_in_range(all_events, float(w2["start_seconds"]), float(w2["end_seconds"])))
        if not (c1 > c0 and c2 < c1):
            continue
        meter_support = _clamp(_safe_float(meter_payload.get("confidence"), 0.0))
        pitch_support = _clamp(
            0.2
            + _overlap_count(
                pitch_payload.get("chord_movement", []) if isinstance(pitch_payload.get("chord_movement"), list) else [],
                float(w2["start_seconds"]),
                float(w2["end_seconds"]),
            )
            / 4.0
        )
        make_example(
            task_type="buildup_to_release",
            context_start_seconds=float(w0["start_seconds"]),
            context_end_seconds=float(w1["end_seconds"]),
            target_start_seconds=float(w2["start_seconds"]),
            target_end_seconds=float(w2["end_seconds"]),
            context_midi_ref=merged_midi_path.as_posix() if merged_midi_path else None,
            target_midi_ref=merged_midi_path.as_posix() if merged_midi_path else None,
            motif_strength=_clamp(0.58 + 0.22 * meter_support + 0.2 * pitch_support),
            context_window_id=str(w1["window_id"]),
            target_window_id=str(w2["window_id"]),
            extraction_notes=["density_ramp_arrival_pair", "meter_pitch_support"],
        )

    # J. Infill.
    for i in range(len(windows) - 2):
        before = windows[i]
        middle = windows[i + 1]
        after = windows[i + 2]
        before_events = _events_in_range(all_events, float(before["start_seconds"]), float(before["end_seconds"]))
        after_events = _events_in_range(all_events, float(after["start_seconds"]), float(after["end_seconds"]))
        middle_events = _events_in_range(all_events, float(middle["start_seconds"]), float(middle["end_seconds"]))
        informative_context = len(before_events) >= 2 and len(after_events) >= 2
        if not informative_context:
            continue
        if len(middle_events) < max(2, int(TASK_POLICIES["infill_missing_region"].get("minimum_note_count", 1))):
            continue
        make_example(
            task_type="infill_missing_region",
            context_start_seconds=float(before["start_seconds"]),
            context_end_seconds=float(after["end_seconds"]),
            target_start_seconds=float(middle["start_seconds"]),
            target_end_seconds=float(middle["end_seconds"]),
            context_midi_ref=merged_midi_path.as_posix() if merged_midi_path else None,
            target_midi_ref=str(middle.get("midi_path") or merged_midi_path.as_posix() if merged_midi_path else ""),
            motif_strength=0.52,
            context_window_id=str(before["window_id"]),
            target_window_id=str(middle["window_id"]),
            extraction_notes=["informative_before_after_context"],
        )

    split_counts = Counter(str(item.get("split_recommendation", "review")) for item in examples)
    task_counts = Counter(str(item.get("task_type", "unknown")) for item in examples)
    quality_values = [_safe_float(item.get("quality_score", {}).get("final_score"), 0.0) for item in examples]
    avg_quality = round(mean(quality_values), 6) if quality_values else 0.0
    duration_seconds = _safe_float(segments_manifest.get("duration_seconds"), 0.0)
    examples_per_minute = round((len(examples) / max(1e-6, duration_seconds)) * 60.0, 6) if duration_seconds > 0 else 0.0
    high_quality_count = sum(1 for item in examples if _safe_float(item.get("quality_score", {}).get("final_score"), 0.0) >= SPLIT_THRESHOLDS["train"])
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
        "generative_examples_count": len(examples),
        "split_counts": dict(sorted(split_counts.items())),
        "examples_by_task_type": dict(sorted(task_counts.items())),
        "average_quality_score": avg_quality,
        "examples_per_minute": examples_per_minute,
        "high_quality_examples_per_minute": high_quality_examples_per_minute,
        "high_quality_examples_count": high_quality_count,
        "missing_task_coverage": missing_task_coverage,
        "split_reason_breakdown_exclude": dict(sorted(exclusion_stats.items())),
        "split_reason_breakdown_review": dict(sorted(review_stats.items())),
        "task_extraction_counts": dict(sorted(extraction_stats.items())),
        "trust_policy_note": "Weak labels may be used for conditioning only and are never promoted to ground truth.",
    }

    jsonl_path = out_dir / "generative_examples.jsonl"
    manifest_path = out_dir / "generative_manifest.json"
    summary_path = out_dir / "generative_summary.md"
    jsonl_path.write_text(
        "\n".join(json.dumps(item, ensure_ascii=True) for item in examples) + ("\n" if examples else ""),
        encoding="utf-8",
    )
    save_json(manifest_path, manifest)

    lines = [
        f"# Generative Dataset Summary - {ctx['performance_id']}",
        "",
        f"- segment_run_id: `{ctx['segment_run_id']}`",
        f"- generative_examples_count: `{len(examples)}`",
        f"- average_quality_score: `{avg_quality}`",
        f"- examples_per_minute: `{examples_per_minute}`",
        f"- high_quality_examples_per_minute: `{high_quality_examples_per_minute}`",
        f"- missing_task_coverage: `{json.dumps(missing_task_coverage, ensure_ascii=True)}`",
        "",
        "## Split counts",
    ]
    for split_name, count in sorted(split_counts.items()):
        lines.append(f"- {split_name}: `{count}`")
    lines.extend(["", "## Examples by task type"])
    for task_name, count in sorted(task_counts.items()):
        lines.append(f"- {task_name}: `{count}`")
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return jsonl_path.resolve(), manifest_path.resolve(), summary_path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Build generative music training examples from existing artifacts.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    args = parser.parse_args()
    jsonl_path, manifest_path, summary_path = build_generative_training_examples(Path(args.performance_manifest))
    print(f"GENERATIVE_EXAMPLES_JSONL={jsonl_path.as_posix()}")
    print(f"GENERATIVE_MANIFEST_JSON={manifest_path.as_posix()}")
    print(f"GENERATIVE_SUMMARY_MD={summary_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

