from __future__ import annotations

from features.local_rendering.chordpotion_intent_schema import ChordPotionTargetIntent, ChordPotionTargetPatternFamily
from features.local_rendering.chordpotion_output_analysis import ChordPotionOutputAnalysis
from features.local_rendering.chordpotion_preset_registry import ChordPotionPresetProfile
from features.local_rendering.chordpotion_scoring import score_candidate_against_intent


def _intent() -> ChordPotionTargetIntent:
    return ChordPotionTargetIntent(
        intent_id="i",
        source_generation_id="g",
        target_role="chord_pattern_generator",
        source_chord_skeleton="x.mid",
        target_pattern_family=ChordPotionTargetPatternFamily.ROLLING_CHORD_MOTION,
        target_density=0.4,
        target_syncopation=0.4,
        target_motion=0.6,
        target_repetition=0.4,
        target_variation=0.6,
        target_humanization=0.4,
        target_register_behavior="mid",
        preserve_bass=True,
        preserve_top_voice=True,
        preserve_harmonic_rhythm=True,
        preserve_chord_identity=True,
        avoid_mud=True,
        avoid_random_keyboard_effect=True,
        avoid_overbusy_output=True,
        avoid_lead_conflict=True,
        desired_ear_effect="flow",
        texture_profile="warm",
        theory_profile="functional",
        confidence=0.8,
    )


def _preset() -> ChordPotionPresetProfile:
    return ChordPotionPresetProfile(
        preset_id="p1",
        display_name="Preset 1",
        local_preset_name="Preset 1",
        category="test",
        expected_pattern_family="rolling_chord_motion",
        expected_density=0.4,
        expected_syncopation=0.4,
        expected_motion=0.6,
        expected_register_behavior="mid",
        expected_texture="warm",
    )


def test_scoring_rewards_preservation_and_motion() -> None:
    good = ChordPotionOutputAnalysis(40, 0.4, 0.3, 6, 0.5, 0.4, 0.8, 0.9, 0.1, 0.1, 0.1, 0.6, 0.1, 0.5, 0.4, 0.6, 0.5, 0.1, 0.1, 0.7, 0.8)
    bad = ChordPotionOutputAnalysis(180, 0.9, 0.9, 15, 0.1, 0.9, 0.2, 0.2, 0.8, 0.8, 0.7, 0.2, 0.9, 0.1, 0.1, 0.9, 0.1, 0.9, 0.9, 0.2, 0.2)
    good_score = score_candidate_against_intent(_intent(), _preset(), good)
    bad_score = score_candidate_against_intent(_intent(), _preset(), bad)
    assert good_score.overall_candidate_score > bad_score.overall_candidate_score
    assert bad_score.overbusy_penalty >= good_score.overbusy_penalty
