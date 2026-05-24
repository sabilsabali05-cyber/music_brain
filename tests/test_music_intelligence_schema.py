from __future__ import annotations

from features.music_intelligence.music_intelligence_schema import MusicIntelligenceRecord, clamp_score


def test_score_clamping_bounds() -> None:
    assert clamp_score(-1.0) == 0.0
    assert clamp_score(2.0) == 1.0
    assert clamp_score(0.42) == 0.42


def test_private_paths_are_redacted_in_record() -> None:
    row = {
        "item_id": "item_1",
        "source_artifact": "datasets/training_exports/example.jsonl",
        "source_path_redacted": r"C:\Users\izzyo\ai-composer\music_brain\secret.mid",
        "authorization_status": "accepted",
        "training_allowed": False,
        "retrieval_allowed": True,
        "policy_status": "complete",
        "keep_reject_label": "keep",
        "harmony_quality": 7,
        "rhythm_quality": 7,
        "texture_quality": 7,
        "arrangement_quality": 7,
        "melody_quality": 7,
        "musicality_quality": 7,
    }
    record = MusicIntelligenceRecord.from_normalized_row(row)
    assert "<PRIVATE_LOCAL_PATH>" in record.source_path_redacted
    assert "C:\\Users\\izzyo" not in record.source_path_redacted


def test_source_url_is_redacted() -> None:
    row = {
        "item_id": "item_2",
        "source_artifact": "datasets/training_exports/example.jsonl",
        "source_path_redacted": "https://youtube.com/watch?v=abc",
        "authorization_status": "unknown",
        "training_allowed": False,
        "retrieval_allowed": True,
        "policy_status": "missing_fields",
        "keep_reject_label": "unlabeled",
    }
    record = MusicIntelligenceRecord.from_normalized_row(row)
    assert "<REDACTED_URL>" in record.source_path_redacted
