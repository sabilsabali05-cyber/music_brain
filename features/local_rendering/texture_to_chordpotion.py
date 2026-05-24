from __future__ import annotations

from .chordpotion_schema import ChordPotionMapping, ChordPotionPatternIntent


def map_texture_to_chordpotion(texture_intent: str) -> ChordPotionMapping:
    texture = texture_intent.lower().strip()
    if "ambient" in texture or "pad" in texture:
        return ChordPotionMapping(
            pattern_intent=ChordPotionPatternIntent.LOW_CLUTTER,
            rhythm_density="low",
            gate_ratio=0.82,
            note_probability=0.58,
            voicing_spread="wide",
            movement_bias="sustained",
            humanize_amount="subtle",
            notes=["Ambient/pad textures keep sparse timing and long gates."],
        )
    if "lead" in texture or "foreground" in texture:
        return ChordPotionMapping(
            pattern_intent=ChordPotionPatternIntent.VOICINGS_2_TO_5_NOTES,
            rhythm_density="medium",
            gate_ratio=0.62,
            note_probability=0.7,
            voicing_spread="narrow_mid",
            movement_bias="counter_to_lead",
            humanize_amount="light",
            notes=["Stay out of lead range and avoid dense upper-register stacks."],
        )
    if "rhyth" in texture or "groove" in texture:
        return ChordPotionMapping(
            pattern_intent=ChordPotionPatternIntent.HUMANIZED_TIMING,
            rhythm_density="medium_high",
            gate_ratio=0.56,
            note_probability=0.83,
            voicing_spread="mid",
            movement_bias="syncopated",
            humanize_amount="medium",
            notes=["Rhythmic intent emphasizes groove with controlled humanization."],
        )
    return ChordPotionMapping(
        pattern_intent=ChordPotionPatternIntent.STRONG_MOVEMENT,
        rhythm_density="medium",
        gate_ratio=0.7,
        note_probability=0.78,
        voicing_spread="mid",
        movement_bias="voice_leading",
        humanize_amount="light",
        notes=["Fallback texture mapping keeps movement and avoids clutter."],
    )

