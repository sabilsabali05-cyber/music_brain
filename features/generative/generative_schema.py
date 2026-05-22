from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TypedDict


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConditioningSpec(TypedDict):
    content_state: str
    tempo_context: dict[str, Any]
    meter_hypotheses: list[dict[str, Any]]
    groove_profile: dict[str, Any]
    pitch_center_context: dict[str, Any]
    harmony_context: dict[str, Any]
    interval_profile: dict[str, Any]
    melodic_contour_context: dict[str, Any]
    density_arc_context: dict[str, Any]
    macro_section_context: dict[str, Any]
    style_tags_weak: list[str]
    theory_source_refs: list[str]
    model_source_refs: list[str]


class TargetRepresentation(TypedDict):
    midi_events: list[dict[str, Any]]
    piano_roll_summary: dict[str, Any]
    note_sequence_summary: dict[str, Any]
    rhythm_tokens: list[str]
    pitch_tokens: list[str]
    chord_or_sonority_tokens: list[str]
    contour_tokens: list[str]
    velocity_profile: dict[str, Any]
    timing_deviation_profile: dict[str, Any]
    arrangement_density_profile: dict[str, Any]


class GenerativeQualityScore(TypedDict):
    transcription_reliability: float
    route_suitability: float
    phrase_boundary_quality: float
    target_density: float
    musical_completeness: float
    repetition_or_motif_strength: float
    witness_agreement_score: float
    ambiguity_penalty: float
    review_penalty: float
    final_score: float


class GenerativeExample(TypedDict):
    example_id: str
    performance_id: str
    segment_run_id: str
    task_type: str
    start_seconds: float
    end_seconds: float
    context_start_seconds: float
    context_end_seconds: float
    target_start_seconds: float
    target_end_seconds: float
    audio_ref: str | None
    context_midi_ref: str | None
    target_midi_ref: str | None
    full_midi_ref: str | None
    feature_refs: dict[str, str | None]
    rhythm_time_refs: dict[str, Any]
    pitch_harmony_refs: dict[str, Any]
    routing_refs: dict[str, str | None]
    external_witness_refs: dict[str, str | None]
    consensus_refs: dict[str, str | None]
    input_summary: dict[str, Any]
    target_summary: dict[str, Any]
    conditioning: ConditioningSpec
    target_representation: TargetRepresentation
    loss_domains: list[str]
    trust_policy: dict[str, Any]
    quality_score: GenerativeQualityScore
    novelty_potential_score: float
    limitations: list[str]
    split_recommendation: str
    created_at: str


def generative_example(
    *,
    example_id: str,
    performance_id: str,
    segment_run_id: str,
    task_type: str,
    start_seconds: float,
    end_seconds: float,
    context_start_seconds: float,
    context_end_seconds: float,
    target_start_seconds: float,
    target_end_seconds: float,
    audio_ref: str | None,
    context_midi_ref: str | None,
    target_midi_ref: str | None,
    full_midi_ref: str | None,
    feature_refs: dict[str, str | None],
    rhythm_time_refs: dict[str, Any],
    pitch_harmony_refs: dict[str, Any],
    routing_refs: dict[str, str | None],
    external_witness_refs: dict[str, str | None],
    consensus_refs: dict[str, str | None],
    input_summary: dict[str, Any],
    target_summary: dict[str, Any],
    conditioning: ConditioningSpec,
    target_representation: TargetRepresentation,
    loss_domains: list[str],
    trust_policy: dict[str, Any],
    quality_score: GenerativeQualityScore,
    novelty_potential_score: float,
    limitations: list[str],
    split_recommendation: str,
) -> GenerativeExample:
    return {
        "example_id": example_id,
        "performance_id": performance_id,
        "segment_run_id": segment_run_id,
        "task_type": task_type,
        "start_seconds": round(float(start_seconds), 6),
        "end_seconds": round(float(end_seconds), 6),
        "context_start_seconds": round(float(context_start_seconds), 6),
        "context_end_seconds": round(float(context_end_seconds), 6),
        "target_start_seconds": round(float(target_start_seconds), 6),
        "target_end_seconds": round(float(target_end_seconds), 6),
        "audio_ref": audio_ref,
        "context_midi_ref": context_midi_ref,
        "target_midi_ref": target_midi_ref,
        "full_midi_ref": full_midi_ref,
        "feature_refs": feature_refs,
        "rhythm_time_refs": rhythm_time_refs,
        "pitch_harmony_refs": pitch_harmony_refs,
        "routing_refs": routing_refs,
        "external_witness_refs": external_witness_refs,
        "consensus_refs": consensus_refs,
        "input_summary": input_summary,
        "target_summary": target_summary,
        "conditioning": conditioning,
        "target_representation": target_representation,
        "loss_domains": [str(item) for item in loss_domains],
        "trust_policy": trust_policy,
        "quality_score": quality_score,
        "novelty_potential_score": round(float(novelty_potential_score), 6),
        "limitations": [str(item) for item in limitations],
        "split_recommendation": split_recommendation,
        "created_at": _now_iso(),
    }
