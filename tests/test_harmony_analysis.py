from __future__ import annotations

from features.music_theory_understanding.harmony_analysis import analyze_harmony


def test_harmony_marks_valuable_weirdness_not_random_clash() -> None:
    row = {"harmony_quality": 8, "weirdness_quality": 8, "tags": ["chromatic"]}
    understanding, scores = analyze_harmony(row, 0.8)
    assert understanding.valuable_weirdness is True
    assert scores["harmonic_interest_score"] > 0.5


def test_harmony_not_applicable_for_sparse_evidence() -> None:
    row = {"harmony_quality": None, "weirdness_quality": None, "tags": []}
    understanding, _ = analyze_harmony(row, 0.1)
    assert understanding.not_applicable is True
