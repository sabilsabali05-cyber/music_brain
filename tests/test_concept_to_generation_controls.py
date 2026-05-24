from __future__ import annotations

from features.concept_to_composition.concept_to_generation_controls import build_generation_controls
from features.concept_to_composition.conversation_parser import parse_conversation_to_brief


def test_emotional_language_maps_to_musical_controls() -> None:
    brief = parse_conversation_to_brief("dark and hopeful with sparse rhythm and emotional chords")
    controls, _interpreted = build_generation_controls(brief, "harmony_first")
    assert controls.target_tempo >= brief.tempo_range.min_bpm
    assert controls.target_tempo <= brief.tempo_range.max_bpm
    assert controls.preserve_emotional_chord_movement is True
    assert controls.avoid_random_leaps is True


def test_avoid_and_preserve_patterns_are_applied() -> None:
    brief = parse_conversation_to_brief("weird but musical and preserve motif")
    controls, _interpreted = build_generation_controls(brief, "weird_but_musical")
    assert controls.avoid_patterns_applied
    assert controls.preserve_patterns_applied
