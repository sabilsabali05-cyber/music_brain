from __future__ import annotations

from features.music_intelligence.music_intelligence_schema import MusicIntelligenceRecord
from features.music_intelligence.music_intelligence_scoring import compute_music_intelligence_scores


def test_scores_are_clamped_between_zero_and_one() -> None:
    row = {
        "item_id": "score_1",
        "source_artifact": "datasets/training_exports/example.jsonl",
        "source_path_redacted": "datasets/training_exports/example.mid",
        "authorization_status": "accepted",
        "training_allowed": True,
        "retrieval_allowed": True,
        "policy_status": "complete",
        "keep_reject_label": "keep",
        "harmony_quality": 20,
        "melody_quality": 20,
        "rhythm_quality": 20,
        "texture_quality": 20,
        "arrangement_quality": 20,
        "emotional_quality": 20,
        "weirdness_quality": 20,
        "musicality_quality": 20,
        "human_rating": 20,
    }
    record = MusicIntelligenceRecord.from_normalized_row(row)
    scores = compute_music_intelligence_scores(record)
    for value in scores.values():
        assert 0.0 <= float(value) <= 1.0


def test_missing_labels_force_training_value_zero() -> None:
    row = {
        "item_id": "score_2",
        "source_artifact": "datasets/training_exports/example.jsonl",
        "source_path_redacted": "datasets/training_exports/example.mid",
        "authorization_status": "accepted",
        "training_allowed": True,
        "retrieval_allowed": True,
        "policy_status": "complete",
        "keep_reject_label": "unlabeled",
        "harmony_quality": 8,
        "melody_quality": 8,
        "rhythm_quality": 8,
        "texture_quality": 8,
        "arrangement_quality": 8,
        "musicality_quality": 8,
        "human_rating": 9,
    }
    record = MusicIntelligenceRecord.from_normalized_row(row)
    scores = compute_music_intelligence_scores(record)
    assert scores["training_value_score"] == 0.0
