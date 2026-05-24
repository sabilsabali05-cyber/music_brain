from __future__ import annotations

from features.local_rendering.chordpotion_schema import ChordPotionPatternIntent
from features.local_rendering.theory_to_chordpotion import map_theory_to_chordpotion


def test_theory_mapping_prefers_strong_movement() -> None:
    mapping = map_theory_to_chordpotion("strong", "medium", "weak")
    assert mapping.pattern_intent == ChordPotionPatternIntent.STRONG_MOVEMENT
    assert mapping.note_probability > 0.8


def test_theory_mapping_respects_low_complexity() -> None:
    mapping = map_theory_to_chordpotion("moderate", "low", "weak")
    assert mapping.pattern_intent == ChordPotionPatternIntent.LOW_CLUTTER
    assert mapping.rhythm_density == "low"

