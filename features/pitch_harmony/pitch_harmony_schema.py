from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _base_record(
    *,
    record_type: str,
    performance_id: str,
    source_name: str,
    segment_run_id: str,
    start_seconds: float,
    end_seconds: float,
    confidence: float,
    limitations: list[str],
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "record_type": record_type,
        "performance_id": performance_id,
        "source_name": source_name,
        "segment_run_id": segment_run_id,
        "start_seconds": round(float(start_seconds), 6),
        "end_seconds": round(float(end_seconds), 6),
        "duration_seconds": round(max(0.0, float(end_seconds) - float(start_seconds)), 6),
        "confidence": round(float(confidence), 6),
        "limitations": [str(item) for item in limitations],
        "evidence": evidence or {},
        "created_at": _now_iso(),
    }


def PitchObservationRecord(
    *,
    performance_id: str,
    source_name: str,
    segment_run_id: str,
    start_seconds: float,
    end_seconds: float,
    confidence: float,
    limitations: list[str],
    pitch_range: dict[str, Any],
    register_distribution: dict[str, Any],
    pitch_class_histogram: dict[str, Any],
    pitch_center_candidates: list[dict[str, Any]],
    pitch_stability_salience: dict[str, Any],
    microtonal_placeholders: dict[str, Any],
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _base_record(
        record_type="pitch_observation_record",
        performance_id=performance_id,
        source_name=source_name,
        segment_run_id=segment_run_id,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        confidence=confidence,
        limitations=limitations,
        evidence=evidence,
    )
    payload["pitch_range"] = pitch_range
    payload["register_distribution"] = register_distribution
    payload["pitch_class_histogram"] = pitch_class_histogram
    payload["pitch_center_candidates"] = pitch_center_candidates
    payload["pitch_stability_salience"] = pitch_stability_salience
    payload["microtonal_placeholders"] = microtonal_placeholders
    return payload


def IntervalRecord(
    *,
    performance_id: str,
    source_name: str,
    segment_run_id: str,
    start_seconds: float,
    end_seconds: float,
    confidence: float,
    limitations: list[str],
    melodic_interval_distribution: dict[str, int],
    harmonic_interval_distribution: dict[str, int],
    interval_class_histogram: dict[str, int],
    interval_family_metrics: dict[str, float],
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _base_record(
        record_type="interval_record",
        performance_id=performance_id,
        source_name=source_name,
        segment_run_id=segment_run_id,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        confidence=confidence,
        limitations=limitations,
        evidence=evidence,
    )
    payload["melodic_interval_distribution"] = melodic_interval_distribution
    payload["harmonic_interval_distribution"] = harmonic_interval_distribution
    payload["interval_class_histogram"] = interval_class_histogram
    payload["interval_family_metrics"] = interval_family_metrics
    return payload


def MelodyContourRecord(
    *,
    performance_id: str,
    source_name: str,
    segment_run_id: str,
    start_seconds: float,
    end_seconds: float,
    confidence: float,
    limitations: list[str],
    contour_tokens: str,
    contour_shape_candidates: list[dict[str, Any]],
    phrase_movement_summary: dict[str, Any],
    motif_sequence_candidates: list[dict[str, Any]],
    cadence_arrival_candidates: list[dict[str, Any]],
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _base_record(
        record_type="melody_contour_record",
        performance_id=performance_id,
        source_name=source_name,
        segment_run_id=segment_run_id,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        confidence=confidence,
        limitations=limitations,
        evidence=evidence,
    )
    payload["contour_tokens"] = contour_tokens
    payload["contour_shape_candidates"] = contour_shape_candidates
    payload["phrase_movement_summary"] = phrase_movement_summary
    payload["motif_sequence_candidates"] = motif_sequence_candidates
    payload["cadence_arrival_candidates"] = cadence_arrival_candidates
    return payload


def HarmonySonorityRecord(
    *,
    performance_id: str,
    source_name: str,
    segment_run_id: str,
    start_seconds: float,
    end_seconds: float,
    confidence: float,
    limitations: list[str],
    pitch_class_set: list[int],
    voicing_span_semitones: float,
    sonority_type_candidate: str,
    sonority_hypotheses: list[dict[str, Any]],
    chord_candidates: list[dict[str, Any]],
    extension_alteration_candidates: list[str],
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _base_record(
        record_type="harmony_sonority_record",
        performance_id=performance_id,
        source_name=source_name,
        segment_run_id=segment_run_id,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        confidence=confidence,
        limitations=limitations,
        evidence=evidence,
    )
    payload["pitch_class_set"] = [int(item) for item in pitch_class_set]
    payload["voicing_span_semitones"] = round(float(voicing_span_semitones), 6)
    payload["sonority_type_candidate"] = sonority_type_candidate
    payload["sonority_hypotheses"] = sonority_hypotheses
    payload["chord_candidates"] = chord_candidates
    payload["extension_alteration_candidates"] = extension_alteration_candidates
    return payload


def ChordMovementRecord(
    *,
    performance_id: str,
    source_name: str,
    segment_run_id: str,
    start_seconds: float,
    end_seconds: float,
    confidence: float,
    limitations: list[str],
    root_motion_candidates: list[dict[str, Any]],
    bass_motion_candidates: list[dict[str, Any]],
    common_tone_count: int,
    voice_leading_proxy: dict[str, Any],
    movement_metrics: dict[str, float],
    cadence_modulation_candidates: list[dict[str, Any]],
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _base_record(
        record_type="chord_movement_record",
        performance_id=performance_id,
        source_name=source_name,
        segment_run_id=segment_run_id,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        confidence=confidence,
        limitations=limitations,
        evidence=evidence,
    )
    payload["root_motion_candidates"] = root_motion_candidates
    payload["bass_motion_candidates"] = bass_motion_candidates
    payload["common_tone_count"] = int(common_tone_count)
    payload["voice_leading_proxy"] = voice_leading_proxy
    payload["movement_metrics"] = movement_metrics
    payload["cadence_modulation_candidates"] = cadence_modulation_candidates
    return payload


def CounterpointRecord(
    *,
    performance_id: str,
    source_name: str,
    segment_run_id: str,
    start_seconds: float,
    end_seconds: float,
    confidence: float,
    limitations: list[str],
    voice_count_estimate: int,
    motion_proxy_summary: dict[str, float],
    imitation_call_response_candidates: list[dict[str, Any]],
    independence_summary: dict[str, float],
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _base_record(
        record_type="counterpoint_record",
        performance_id=performance_id,
        source_name=source_name,
        segment_run_id=segment_run_id,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        confidence=confidence,
        limitations=limitations,
        evidence=evidence,
    )
    payload["voice_count_estimate"] = int(voice_count_estimate)
    payload["motion_proxy_summary"] = motion_proxy_summary
    payload["imitation_call_response_candidates"] = imitation_call_response_candidates
    payload["independence_summary"] = independence_summary
    return payload


def TuningSystemRecord(
    *,
    performance_id: str,
    source_name: str,
    segment_run_id: str,
    start_seconds: float,
    end_seconds: float,
    confidence: float,
    limitations: list[str],
    microtonal_analysis_available: bool,
    microtonal_evidence_type: str,
    microtonal_confidence: float,
    tuning_hypotheses: list[dict[str, Any]],
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _base_record(
        record_type="tuning_system_record",
        performance_id=performance_id,
        source_name=source_name,
        segment_run_id=segment_run_id,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        confidence=confidence,
        limitations=limitations,
        evidence=evidence,
    )
    payload["microtonal_analysis_available"] = bool(microtonal_analysis_available)
    payload["microtonal_evidence_type"] = microtonal_evidence_type
    payload["microtonal_confidence"] = round(float(microtonal_confidence), 6)
    payload["tuning_hypotheses"] = tuning_hypotheses
    return payload


def PitchHarmonyMacroRecord(
    *,
    performance_id: str,
    source_name: str,
    segment_run_id: str,
    start_seconds: float,
    end_seconds: float,
    confidence: float,
    limitations: list[str],
    key_hypotheses: list[dict[str, Any]],
    recurring_sonority_families: list[dict[str, Any]],
    register_density_arc: dict[str, Any],
    dissonance_cluster_arc: dict[str, Any],
    macro_form_candidates: list[dict[str, Any]],
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _base_record(
        record_type="pitch_harmony_macro_record",
        performance_id=performance_id,
        source_name=source_name,
        segment_run_id=segment_run_id,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        confidence=confidence,
        limitations=limitations,
        evidence=evidence,
    )
    payload["key_hypotheses"] = key_hypotheses
    payload["recurring_sonority_families"] = recurring_sonority_families
    payload["register_density_arc"] = register_density_arc
    payload["dissonance_cluster_arc"] = dissonance_cluster_arc
    payload["macro_form_candidates"] = macro_form_candidates
    return payload
