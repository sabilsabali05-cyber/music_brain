from __future__ import annotations

from pathlib import Path

from features.taste_learning.composition_ranker import extract_features, score_with_heuristic


def test_ratio_features_are_part_of_candidate_feature_space() -> None:
    features = extract_features({})
    required = {
        "golden_section_alignment",
        "phrase_ratio_score",
        "rhythm_ratio_score",
        "interval_ratio_score",
        "density_ratio_score",
        "ratio_musicality_score",
    }
    assert required.issubset(features.keys())
    score = score_with_heuristic(features)
    assert 0.0 <= score <= 1.0


def test_loop_script_includes_ratio_steps() -> None:
    loop_path = Path("scripts/run_music_understanding_loop.py")
    text = loop_path.read_text(encoding="utf-8")
    assert "analyze_ratio_understanding.py" in text
    assert "generate_ratio_controlled_song.py" in text
    assert "evaluate_ratio_controlled_generation.py" in text

