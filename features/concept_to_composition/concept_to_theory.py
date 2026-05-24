from __future__ import annotations

from .concept_interpreter import InterpretedConcept
from .concept_schema import SongConceptBrief


def build_theory_plan(brief: SongConceptBrief, interpreted: InterpretedConcept, strategy: str) -> dict[str, object]:
    progression = ["Am", "F", "C", "G"]
    if strategy == "harmony_first":
        progression = ["Am9", "Fmaj7", "C(add9)", "Gsus4", "G"]
    elif strategy == "rhythm_first":
        progression = ["Am", "Am", "F", "G"]
    elif strategy == "weird_but_musical":
        progression = ["Am", "Bbmaj7", "F", "E7sus4", "E7"]

    return {
        "key_or_mode": brief.key_or_mode_preference,
        "progression": progression,
        "voice_leading_focus": strategy in {"harmony_first", "weird_but_musical"},
        "theory_hooks_used": interpreted.theory_hooks,
        "preserve_emotional_chord_movement": True,
    }
