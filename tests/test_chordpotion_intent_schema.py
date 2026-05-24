from __future__ import annotations

from pathlib import Path

from features.local_rendering.chordpotion_intent_schema import (
    ChordPotionTargetIntent,
    ChordPotionTargetPatternFamily,
    load_target_intent,
    write_target_intent,
)


def test_intent_schema_roundtrip(tmp_path: Path) -> None:
    intent = ChordPotionTargetIntent(
        intent_id="intent_1",
        source_generation_id="gen_1",
        target_role="chord_pattern_generator",
        source_chord_skeleton="outputs/gen_1/harmony.mid",
        target_pattern_family=ChordPotionTargetPatternFamily.SPARSE_EMOTIONAL_PULSE,
        target_density=0.3,
        target_syncopation=0.2,
        target_motion=0.4,
        target_repetition=0.5,
        target_variation=0.4,
        target_humanization=0.6,
        target_register_behavior="mid_support",
        preserve_bass=True,
        preserve_top_voice=True,
        preserve_harmonic_rhythm=True,
        preserve_chord_identity=True,
        avoid_mud=True,
        avoid_random_keyboard_effect=True,
        avoid_overbusy_output=True,
        avoid_lead_conflict=True,
        desired_ear_effect="movement without clutter",
        texture_profile="warm_pad",
        theory_profile="functional_harmony",
        confidence=0.7,
    )
    path = tmp_path / "intent.json"
    write_target_intent(path, intent)
    loaded = load_target_intent(path)
    assert loaded.target_pattern_family == ChordPotionTargetPatternFamily.SPARSE_EMOTIONAL_PULSE
    assert loaded.preserve_bass is True
