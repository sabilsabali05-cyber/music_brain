from __future__ import annotations

from features.music_theory_understanding.theory_frameworks import infer_framework_applicability


def test_frameworks_include_not_applicable_for_weak_evidence() -> None:
    out = infer_framework_applicability(
        harmonic_strength=0.1,
        chromatic_hint=0.1,
        rhythmic_strength=0.1,
        loop_tendency=0.1,
        texture_strength=0.1,
        microtonal_evidence=False,
        choir_hint=False,
    )
    assert out["western_functional_harmony"].not_applicable is True
    assert out["microtonal_pitch_bend_awareness"].not_applicable is True


def test_frameworks_mark_microtonal_only_when_evidence_present() -> None:
    out = infer_framework_applicability(
        harmonic_strength=0.4,
        chromatic_hint=0.5,
        rhythmic_strength=0.7,
        loop_tendency=0.5,
        texture_strength=0.6,
        microtonal_evidence=True,
        choir_hint=False,
    )
    assert out["microtonal_pitch_bend_awareness"].applicable is True
