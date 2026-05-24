from __future__ import annotations

from features.music_theory_understanding.motif_analysis import analyze_motif


def test_motif_reusability_higher_for_higher_musicality() -> None:
    _, hi = analyze_motif({"musicality_quality": 8, "weirdness_quality": 4}, 0.7)
    _, lo = analyze_motif({"musicality_quality": 2, "weirdness_quality": 1}, 0.7)
    assert hi["motif_reusability_score"] > lo["motif_reusability_score"]
