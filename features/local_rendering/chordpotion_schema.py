from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ChordPotionPatternIntent(str, Enum):
    STRONG_MOVEMENT = "strong_movement"
    LOW_CLUTTER = "low_clutter"
    VOICINGS_2_TO_5_NOTES = "voicings_2_to_5_notes"
    RHYTHMIC_VARIATION = "rhythmic_variation"
    HUMANIZED_TIMING = "humanized_timing"


@dataclass
class ChordPotionMapping:
    pattern_intent: ChordPotionPatternIntent
    rhythm_density: str
    gate_ratio: float
    note_probability: float
    voicing_spread: str
    movement_bias: str
    humanize_amount: str = "light"
    notes: list[str] = field(default_factory=list)

