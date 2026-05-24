from __future__ import annotations

from features.local_rendering.chordpotion_schema import ChordPotionPatternIntent
from features.local_rendering.midi_fx_schema import MidiFxTransformPlan


def test_chordpotion_pattern_intents_stable() -> None:
    values = {item.value for item in ChordPotionPatternIntent}
    assert values == {
        "strong_movement",
        "low_clutter",
        "voicings_2_to_5_notes",
        "rhythmic_variation",
        "humanized_timing",
    }


def test_midi_fx_transform_plan_defaults() -> None:
    plan = MidiFxTransformPlan(
        generation_id="g1",
        input_harmony_midi="a.mid",
        input_bass_midi="b.mid",
        input_lead_guide_midi="c.mid",
        output_transformed_midi="out.mid",
    )
    assert plan.midi_fx_role == "chord_pattern_generator"
    assert plan.bpm == 100
    assert plan.transformed_midi_captured is False

