from __future__ import annotations

from features.music_theory_understanding.voice_leading_analysis import analyze_voice_leading


def test_voice_leading_score_in_range() -> None:
    understanding, scores = analyze_voice_leading({"melody_quality": 6, "arrangement_quality": 7}, 0.8)
    assert 0.0 <= understanding.stepwise_motion_ratio <= 1.0
    assert 0.0 <= scores["voice_leading_score"] <= 1.0


def test_voice_leading_low_confidence_can_be_not_applicable() -> None:
    understanding, _ = analyze_voice_leading({"melody_quality": None, "arrangement_quality": None}, 0.0)
    assert understanding.not_applicable is True
