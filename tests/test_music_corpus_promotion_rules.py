from __future__ import annotations

from features.music_intelligence.music_intelligence_schema import MusicIntelligenceRecord
from features.music_intelligence.music_intelligence_scoring import compute_music_intelligence_scores
from features.music_intelligence.promotion_rules import decide_promotion_label


def _base_row() -> dict:
    return {
        "item_id": "promo_1",
        "source_artifact": "datasets/training_exports/example.jsonl",
        "source_path_redacted": "datasets/training_exports/example.mid",
        "authorization_status": "accepted",
        "training_allowed": True,
        "retrieval_allowed": True,
        "policy_status": "complete",
        "keep_reject_label": "keep",
        "harmony_quality": 8,
        "melody_quality": 8,
        "rhythm_quality": 8,
        "texture_quality": 8,
        "arrangement_quality": 8,
        "emotional_quality": 8,
        "weirdness_quality": 6,
        "musicality_quality": 8,
        "human_rating": 9,
    }


def test_missing_policy_blocks_training_safe() -> None:
    row = _base_row()
    row["policy_status"] = "missing_fields"
    record = MusicIntelligenceRecord.from_normalized_row(row)
    decision = decide_promotion_label(record, compute_music_intelligence_scores(record))
    assert decision.promotion_label != "training_safe"
    assert "policy_fields_incomplete" in decision.blockers


def test_high_music_value_unclear_policy_routes_retrieval_only() -> None:
    row = _base_row()
    row["authorization_status"] = "unknown"
    row["policy_status"] = "missing_fields"
    row["training_allowed"] = False
    record = MusicIntelligenceRecord.from_normalized_row(row)
    decision = decide_promotion_label(record, compute_music_intelligence_scores(record))
    assert decision.promotion_label == "retrieval_only"


def test_junk_or_unauthorized_can_be_excluded() -> None:
    row = _base_row()
    row["authorization_status"] = "private"
    row["excluded_reason"] = "junk_noise"
    record = MusicIntelligenceRecord.from_normalized_row(row)
    decision = decide_promotion_label(record, compute_music_intelligence_scores(record))
    assert decision.promotion_label == "excluded"


def test_deterministic_promotion_decision() -> None:
    row = _base_row()
    record = MusicIntelligenceRecord.from_normalized_row(row)
    scores = compute_music_intelligence_scores(record)
    first = decide_promotion_label(record, scores)
    second = decide_promotion_label(record, scores)
    assert first == second
