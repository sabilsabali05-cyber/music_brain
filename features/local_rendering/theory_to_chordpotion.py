from __future__ import annotations

from .chordpotion_schema import ChordPotionMapping, ChordPotionPatternIntent


def map_theory_to_chordpotion(
    harmonic_movement: str,
    complexity: str,
    cadence_strength: str,
) -> ChordPotionMapping:
    movement = harmonic_movement.lower().strip()
    complexity_value = complexity.lower().strip()
    cadence = cadence_strength.lower().strip()

    if movement in {"strong", "high"}:
        return ChordPotionMapping(
            pattern_intent=ChordPotionPatternIntent.STRONG_MOVEMENT,
            rhythm_density="medium",
            gate_ratio=0.74,
            note_probability=0.88,
            voicing_spread="wide",
            movement_bias="up_down_alternation",
            humanize_amount="light",
            notes=["Prioritize noticeable harmonic motion and phrase-leading momentum."],
        )
    if complexity_value in {"low", "simple"}:
        return ChordPotionMapping(
            pattern_intent=ChordPotionPatternIntent.LOW_CLUTTER,
            rhythm_density="low",
            gate_ratio=0.68,
            note_probability=0.66,
            voicing_spread="mid",
            movement_bias="stepwise",
            humanize_amount="light",
            notes=["Reduce overlap and leave space for bass and lead guides."],
        )
    if cadence in {"strong", "resolved"}:
        return ChordPotionMapping(
            pattern_intent=ChordPotionPatternIntent.VOICINGS_2_TO_5_NOTES,
            rhythm_density="medium",
            gate_ratio=0.72,
            note_probability=0.79,
            voicing_spread="mid_wide",
            movement_bias="voice_leading",
            humanize_amount="light",
            notes=["Use stable 2-5 note voicings around cadence points."],
        )
    return ChordPotionMapping(
        pattern_intent=ChordPotionPatternIntent.RHYTHMIC_VARIATION,
        rhythm_density="medium_high",
        gate_ratio=0.7,
        note_probability=0.75,
        voicing_spread="mid",
        movement_bias="syncopated",
        humanize_amount="light",
        notes=["Balanced default: moderate motion, uncluttered supporting rhythm."],
    )

