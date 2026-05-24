from __future__ import annotations

from features.training_corpus.canonical_music_corpus_schema import normalize_music_corpus_row


def test_missing_training_allowed_defaults_false() -> None:
    row, _stats = normalize_music_corpus_row(
        {"record_id": "r1"},
        source_artifact="datasets/training_exports/example.jsonl",
    )
    assert row["training_allowed"] is False


def test_missing_authorization_and_review_defaults_review_required() -> None:
    row, _stats = normalize_music_corpus_row(
        {"record_id": "r2", "training_allowed": True},
        source_artifact="datasets/training_exports/example.jsonl",
    )
    assert row["authorization_status"] == "review_required"
    assert row["review_status"] == "review_required"


def test_production_only_defaults_to_retrieval_only() -> None:
    row, _stats = normalize_music_corpus_row(
        {"record_id": "r3", "production_only": True},
        source_artifact="datasets/training_exports/example.jsonl",
    )
    assert row["training_allowed"] is False
    assert row["retrieval_allowed"] is True
    assert row["production_use_allowed"] is True


def test_splice_defaults_to_retrieval_only_without_override() -> None:
    row, _stats = normalize_music_corpus_row(
        {"record_id": "r4", "source_name": "splice_loop_001.mid"},
        source_artifact="datasets/training_exports/splice_export.jsonl",
    )
    assert row["training_allowed"] is False
    assert row["retrieval_allowed"] is True


def test_private_paths_are_redacted() -> None:
    row, _stats = normalize_music_corpus_row(
        {"record_id": "r5", "source_path": r"C:\Users\izzyo\ai-composer\music_brain\foo.mid"},
        source_artifact="datasets/training_exports/example.jsonl",
    )
    assert "<PRIVATE_LOCAL_PATH>" in row["source_path_redacted"]
    assert "C:\\Users\\izzyo" not in row["source_path_redacted"]

