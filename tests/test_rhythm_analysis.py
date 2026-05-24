from __future__ import annotations

from features.music_theory_understanding.rhythm_analysis import analyze_rhythm


def test_rhythm_identity_and_groove_scores_clamped() -> None:
    _, scores = analyze_rhythm({"rhythm_quality": 9, "weirdness_quality": 5}, 0.9)
    assert 0.0 <= scores["rhythm_identity_score"] <= 1.0
    assert 0.0 <= scores["groove_value_score"] <= 1.0
