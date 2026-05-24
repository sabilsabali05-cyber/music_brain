from __future__ import annotations

from dataclasses import dataclass

from .concept_interpreter import InterpretedConcept, interpret_concept_language
from .concept_schema import SongConceptBrief


@dataclass(slots=True)
class GenerationControls:
    target_tempo: int
    section_lengths: dict[str, int]
    track_roles: list[str]
    note_density: dict[str, float]
    register_ranges: dict[str, tuple[int, int]]
    velocity_ranges: dict[str, tuple[int, int]]
    chord_movement_rules: list[str]
    motif_reuse_rules: list[str]
    avoid_random_leaps: bool
    preserve_singable_top_line: bool
    preserve_emotional_chord_movement: bool
    avoid_patterns_applied: list[str]
    preserve_patterns_applied: list[str]
    emotional_goals: list[str]
    theory_hooks_used: list[str]
    rhythm_hooks_used: list[str]
    texture_hooks_used: list[str]


def build_generation_controls(brief: SongConceptBrief, strategy: str) -> tuple[GenerationControls, InterpretedConcept]:
    interpreted = interpret_concept_language(brief)
    tempo_midpoint = int(round((brief.tempo_range.min_bpm + brief.tempo_range.max_bpm) / 2))
    tempo = tempo_midpoint
    if strategy == "rhythm_first":
        tempo = min(brief.tempo_range.max_bpm, tempo_midpoint + 4)
    elif strategy == "weird_but_musical":
        tempo = max(brief.tempo_range.min_bpm, tempo_midpoint - 2)

    density = {
        "chords": 0.45,
        "bass": 0.38,
        "lead": 0.34,
        "texture": 0.3,
    }
    if strategy == "rhythm_first":
        density["lead"] = 0.26
        density["bass"] = 0.46
    elif strategy == "harmony_first":
        density["chords"] = 0.52
    elif strategy == "weird_but_musical":
        density["texture"] = 0.42
        density["lead"] = 0.32

    section_lengths = {section.name: section.bars for section in brief.section_plan}

    return (
        GenerationControls(
            target_tempo=tempo,
            section_lengths=section_lengths,
            track_roles=["chords", "bass", "lead", "texture"],
            note_density=density,
            register_ranges={
                "chords": (48, 76),
                "bass": (34, 56),
                "lead": (60, 84),
                "texture": (52, 90),
            },
            velocity_ranges={
                "chords": (45, 92),
                "bass": (50, 96),
                "lead": (52, 102),
                "texture": (35, 82),
            },
            chord_movement_rules=[
                "prefer common tones between adjacent chords",
                "favor stepwise or third-based root motion",
                "retain emotional progression intent from concept",
            ],
            motif_reuse_rules=[
                "reuse primary motif at least once per major section",
                "allow rhythmic variation while preserving contour",
            ],
            avoid_random_leaps=True,
            preserve_singable_top_line=True,
            preserve_emotional_chord_movement=True,
            avoid_patterns_applied=brief.avoid_patterns,
            preserve_patterns_applied=brief.preserve_patterns,
            emotional_goals=interpreted.emotional_goals,
            theory_hooks_used=interpreted.theory_hooks,
            rhythm_hooks_used=interpreted.rhythm_hooks,
            texture_hooks_used=interpreted.texture_hooks,
        ),
        interpreted,
    )
