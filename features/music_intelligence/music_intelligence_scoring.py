from __future__ import annotations

from typing import Any

from .music_intelligence_schema import MusicIntelligenceRecord, clamp_score


def _avg(values: list[float | None]) -> float:
    valid = [value for value in values if value is not None]
    if not valid:
        return 0.0
    return sum(valid) / float(len(valid))


def _sum_moment_scores(moments: list[Any], field_name: str) -> float:
    values: list[float] = []
    for moment in moments:
        raw = getattr(moment, field_name, None)
        if raw is not None:
            values.append(float(raw))
    if not values:
        return 0.0
    return clamp_score(sum(values) / len(values)) or 0.0


def compute_music_intelligence_scores(record: MusicIntelligenceRecord) -> dict[str, float]:
    tempo_structure_score = clamp_score(
        _avg(
            [
                record.tempo_structure.tempo_stability_score,
                record.tempo_structure.structure_clarity_score,
            ]
        )
    ) or 0.0

    harmony_score = clamp_score(
        _avg(
            [
                record.harmony_tonality.harmonic_richness_score,
                # Strong chord movement should raise harmony score.
                record.harmony_tonality.chord_movement_strength_score,
                record.harmony_tonality.tonality_confidence_score,
            ]
        )
    ) or 0.0

    motif_development_score = clamp_score(
        _avg(
            [
                record.tempo_structure.motif_recurrence_score,
                record.bass_melody.motif_development_score,
            ]
        )
    ) or 0.0

    bass_melody_score = clamp_score(
        _avg(
            [
                # Clear bass motion should raise this score.
                record.bass_melody.bass_motion_clarity_score,
                record.bass_melody.melodic_contour_score,
                motif_development_score,
            ]
        )
    ) or 0.0

    groove_stability = record.rhythm.groove_stability_score or 0.0
    rhythmic_complexity = record.rhythm.rhythmic_complexity_score or 0.0
    syncopation_interest = record.rhythm.syncopation_interest_score or 0.0
    rhythmic_intent = max(groove_stability, (rhythmic_complexity + syncopation_interest) / 2.0)
    rhythm_score = clamp_score(_avg([rhythmic_intent, record.rhythm.timing_confidence_score])) or 0.0

    texture_score = clamp_score(
        _avg(
            [
                record.texture_instrumentation.texture_clarity_score,
                record.texture_instrumentation.instrumentation_diversity_score,
                record.texture_instrumentation.arrangement_evolution_score,
            ]
        )
    ) or 0.0

    transcription_reliability_score = clamp_score(record.transcription_confidence) or 0.0
    emotional_value_score = clamp_score(
        _avg([record.emotional_value_score, _sum_moment_scores(record.valuable_moments, "value_score")])
    ) or 0.0
    weirdness_value_score = clamp_score(record.weirdness_value_score) or 0.0

    junk_penalty = clamp_score(
        _avg(
            [
                _sum_moment_scores(record.junk_moments, "junk_score"),
                record.texture_instrumentation.mix_noise_penalty,
            ]
        )
    ) or 0.0

    policy_completeness_score = 1.0
    if not record.policy_outcome.policy_fields_complete:
        policy_completeness_score -= 0.6
    if not record.policy_outcome.labels_complete:
        policy_completeness_score -= 0.25
    if record.policy_outcome.policy_excluded:
        policy_completeness_score = 0.0
    policy_completeness_score = clamp_score(policy_completeness_score) or 0.0

    overall_music_value_score = clamp_score(
        (
            tempo_structure_score
            + harmony_score
            + bass_melody_score
            + rhythm_score
            + texture_score
            + emotional_value_score
            + weirdness_value_score
            + motif_development_score
        )
        / 8.0
        - 0.35 * junk_penalty
    ) or 0.0

    retrieval_value_score = clamp_score(
        0.65 * overall_music_value_score
        + 0.20 * transcription_reliability_score
        + 0.15 * policy_completeness_score
    ) or 0.0

    # Low transcription confidence or missing labels should block supervised training value.
    training_value_score = retrieval_value_score
    if transcription_reliability_score < 0.55:
        training_value_score *= 0.25
    if not record.policy_outcome.policy_fields_complete:
        training_value_score = 0.0
    if not record.policy_outcome.labels_complete:
        training_value_score = 0.0
    training_value_score = clamp_score(training_value_score) or 0.0

    return {
        "tempo_structure_score": tempo_structure_score,
        "harmony_score": harmony_score,
        "bass_melody_score": bass_melody_score,
        "motif_development_score": motif_development_score,
        "rhythm_score": rhythm_score,
        "texture_score": texture_score,
        "transcription_reliability_score": transcription_reliability_score,
        "emotional_value_score": emotional_value_score,
        "weirdness_value_score": weirdness_value_score,
        "junk_penalty": junk_penalty,
        "policy_completeness_score": policy_completeness_score,
        "overall_music_value_score": overall_music_value_score,
        "retrieval_value_score": retrieval_value_score,
        "training_value_score": training_value_score,
    }
