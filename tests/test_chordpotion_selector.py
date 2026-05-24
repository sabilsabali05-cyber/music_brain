from __future__ import annotations

from pathlib import Path

from features.local_rendering.chordpotion_intent_schema import ChordPotionTargetIntent, ChordPotionTargetPatternFamily
from features.local_rendering.chordpotion_preset_registry import ChordPotionPresetProfile
from features.local_rendering.chordpotion_selector import choose_selector_mode, select_candidate_presets


def _intent() -> ChordPotionTargetIntent:
    return ChordPotionTargetIntent(
        intent_id="intent",
        source_generation_id="gen",
        target_role="chord_pattern_generator",
        source_chord_skeleton="x.mid",
        target_pattern_family=ChordPotionTargetPatternFamily.ROLLING_CHORD_MOTION,
        target_density=0.5,
        target_syncopation=0.4,
        target_motion=0.6,
        target_repetition=0.5,
        target_variation=0.5,
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
        desired_ear_effect="musical",
        texture_profile="warm",
        theory_profile="functional",
        confidence=0.6,
    )


def test_selector_mode_honesty() -> None:
    assert choose_selector_mode(0, 0, False) == "heuristic_selector"
    assert choose_selector_mode(3, 1, False) == "feedback_ranker_selector"
    assert choose_selector_mode(21, 2, True) == "trained_selector"


def test_intent_change_can_change_selected_preset(tmp_path: Path) -> None:
    p1 = ChordPotionPresetProfile("p1", "P1", "P1", "cat", "rolling_chord_motion", 0.5, 0.4, 0.6, "mid", "warm")
    p2 = ChordPotionPresetProfile("p2", "P2", "P2", "cat", "dense_experimental_pattern", 0.8, 0.8, 0.8, "wide", "dense")
    feedback = tmp_path / "feedback.jsonl"
    outcomes = tmp_path / "outcomes.jsonl"
    feedback.write_text("", encoding="utf-8")
    outcomes.write_text("", encoding="utf-8")
    decision = select_candidate_presets(_intent(), "functional", "warm", [p1, p2], outcomes, feedback, top_k=1)
    assert decision.selector_mode == "heuristic_selector"
    assert decision.candidate_presets[0].preset_id == "p1"
