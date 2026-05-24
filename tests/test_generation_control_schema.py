from __future__ import annotations

from features.controlled_generation.generation_control_schema import GenerationControlSpec, RatioControl


def test_ratio_control_normalizes_values() -> None:
    control = RatioControl(
        ratio_name="3:2",
        target_ratio=1.5,
        measured_ratio=None,
        tolerance=-1.0,
        confidence=2.0,
        strict=False,
    )
    assert control.tolerance > 0
    assert control.confidence == 1.0


def test_generation_control_spec_clamps_priorities() -> None:
    spec = GenerationControlSpec(
        spec_id="spec1",
        generation_id="gen1",
        duration_seconds=-20,
        bpm=0,
        ratio_controls=[],
        preserve_battle_appeal_priority=True,
        flexibility_priority=2.0,
        ratio_musicality_weight=-1.0,
        evidence_based_only=True,
        no_cloud_calls=True,
    )
    assert spec.duration_seconds >= 1.0
    assert spec.bpm >= 30
    assert spec.flexibility_priority == 1.0
    assert spec.ratio_musicality_weight == 0.0

