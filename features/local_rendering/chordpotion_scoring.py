from __future__ import annotations

from dataclasses import dataclass

from .chordpotion_intent_schema import ChordPotionTargetIntent
from .chordpotion_output_analysis import ChordPotionOutputAnalysis
from .chordpotion_preset_registry import ChordPotionPresetProfile


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _match(target: float, observed: float) -> float:
    return _clamp(1.0 - abs(target - observed))


@dataclass
class ChordPotionCandidateScore:
    pattern_family_match: float
    density_match: float
    syncopation_match: float
    motion_match: float
    chord_identity_preservation: float
    voice_leading_preservation: float
    bass_conflict_avoidance: float
    lead_conflict_avoidance: float
    clutter_control: float
    emotional_support: float
    texture_fit: float
    theory_fit: float
    random_keyboard_penalty: float
    overbusy_penalty: float
    muddy_register_penalty: float
    unresolved_clash_penalty: float
    destroys_chord_identity_penalty: float
    fights_lead_penalty: float
    too_static_penalty: float
    too_generic_penalty: float
    overall_candidate_score: float

    def as_dict(self) -> dict:
        return {
            key: float(value)
            for key, value in self.__dict__.items()
        }


def score_candidate_against_intent(
    intent: ChordPotionTargetIntent,
    preset: ChordPotionPresetProfile,
    analysis: ChordPotionOutputAnalysis,
    theory_profile: str = "",
    texture_profile: str = "",
) -> ChordPotionCandidateScore:
    pattern_family_match = 1.0 if preset.expected_pattern_family == intent.target_pattern_family.value else 0.45
    density_match = _match(intent.target_density, analysis.note_density)
    syncopation_match = _match(intent.target_syncopation, analysis.syncopation_score)
    motion_match = _match(intent.target_motion, analysis.musical_motion_score)
    chord_identity_preservation = analysis.chord_tone_preservation
    voice_leading_preservation = _clamp(1.0 - analysis.non_chord_tone_rate)
    bass_conflict_avoidance = _clamp(1.0 - analysis.bass_interference)
    lead_conflict_avoidance = _clamp(1.0 - analysis.top_voice_interference)
    clutter_control = _clamp(1.0 - analysis.overbusy_penalty)
    emotional_support = analysis.emotional_support_score
    texture_fit = 1.0 if texture_profile and texture_profile.lower() in preset.expected_texture.lower() else 0.55
    theory_fit = 1.0 if theory_profile and theory_profile.lower() in " ".join(preset.known_good_for).lower() else 0.5

    random_keyboard_penalty = analysis.random_keyboard_penalty
    overbusy_penalty = analysis.overbusy_penalty
    muddy_register_penalty = _clamp(analysis.middle_register_mud)
    unresolved_clash_penalty = _clamp((analysis.non_chord_tone_rate + analysis.bass_interference) * 0.5)
    destroys_chord_identity_penalty = _clamp(1.0 - chord_identity_preservation)
    fights_lead_penalty = _clamp(analysis.top_voice_interference)
    too_static_penalty = _clamp(0.5 - analysis.pattern_variation) if analysis.pattern_variation < 0.5 else 0.0
    too_generic_penalty = _clamp(0.4 - analysis.musical_motion_score) if analysis.musical_motion_score < 0.4 else 0.0

    reward = (
        pattern_family_match * 0.10
        + density_match * 0.10
        + syncopation_match * 0.10
        + motion_match * 0.10
        + chord_identity_preservation * 0.12
        + voice_leading_preservation * 0.08
        + bass_conflict_avoidance * 0.08
        + lead_conflict_avoidance * 0.08
        + clutter_control * 0.08
        + emotional_support * 0.08
        + texture_fit * 0.04
        + theory_fit * 0.04
    )
    penalty = (
        random_keyboard_penalty * 0.12
        + overbusy_penalty * 0.12
        + muddy_register_penalty * 0.08
        + unresolved_clash_penalty * 0.08
        + destroys_chord_identity_penalty * 0.12
        + fights_lead_penalty * 0.10
        + too_static_penalty * 0.08
        + too_generic_penalty * 0.08
    )
    overall_candidate_score = _clamp(reward - penalty + 0.45)

    return ChordPotionCandidateScore(
        pattern_family_match=pattern_family_match,
        density_match=density_match,
        syncopation_match=syncopation_match,
        motion_match=motion_match,
        chord_identity_preservation=chord_identity_preservation,
        voice_leading_preservation=voice_leading_preservation,
        bass_conflict_avoidance=bass_conflict_avoidance,
        lead_conflict_avoidance=lead_conflict_avoidance,
        clutter_control=clutter_control,
        emotional_support=emotional_support,
        texture_fit=texture_fit,
        theory_fit=theory_fit,
        random_keyboard_penalty=random_keyboard_penalty,
        overbusy_penalty=overbusy_penalty,
        muddy_register_penalty=muddy_register_penalty,
        unresolved_clash_penalty=unresolved_clash_penalty,
        destroys_chord_identity_penalty=destroys_chord_identity_penalty,
        fights_lead_penalty=fights_lead_penalty,
        too_static_penalty=too_static_penalty,
        too_generic_penalty=too_generic_penalty,
        overall_candidate_score=overall_candidate_score,
    )


def select_best_candidate(scores_by_preset_id: dict[str, ChordPotionCandidateScore]) -> str:
    if not scores_by_preset_id:
        return ""
    return max(scores_by_preset_id.items(), key=lambda item: item[1].overall_candidate_score)[0]
