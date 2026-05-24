from __future__ import annotations

import json
from pathlib import Path

from scripts.promote_reviewed_corpus_splits import promote_reviewed_corpus_splits


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_only_accepted_training_allowed_rows_are_promoted(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    normalized = tmp_path / "datasets" / "normalized_music_corpus" / "normalized_music_corpus.jsonl"
    _write_jsonl(
        normalized,
        [
            {
                "item_id": "train_a",
                "review_status": "accepted",
                "training_allowed": True,
                "policy_status": "complete",
                "keep_reject_label": "keep",
                "human_rating": 8,
                "source_type": "training_export",
            },
            {
                "item_id": "review_b",
                "review_status": "review_required",
                "training_allowed": True,
                "policy_status": "complete",
                "keep_reject_label": "keep",
                "human_rating": 9,
                "source_type": "training_export",
            },
            {
                "item_id": "prod_c",
                "review_status": "accepted",
                "training_allowed": False,
                "policy_status": "complete",
                "keep_reject_label": "keep",
                "human_rating": 9,
                "source_type": "training_export",
            },
        ],
    )
    report = promote_reviewed_corpus_splits(normalized)
    train_rows = _read_jsonl(tmp_path / "datasets" / "training_corpus" / "train.jsonl")
    validation_rows = _read_jsonl(tmp_path / "datasets" / "training_corpus" / "validation.jsonl")
    promoted_ids = {row["item_id"] for row in train_rows + validation_rows}
    assert "train_a" in promoted_ids
    assert "review_b" not in promoted_ids
    assert "prod_c" not in promoted_ids
    assert report["review_required_rows"] >= 1


def test_split_is_deterministic(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    normalized = tmp_path / "datasets" / "normalized_music_corpus" / "normalized_music_corpus.jsonl"
    _write_jsonl(
        normalized,
        [
            {
                "item_id": "deterministic_01",
                "review_status": "accepted",
                "training_allowed": True,
                "policy_status": "complete",
                "keep_reject_label": "keep",
                "human_rating": 7,
                "source_type": "training_export",
            }
        ],
    )
    first = promote_reviewed_corpus_splits(normalized)
    train_first = _read_jsonl(tmp_path / "datasets" / "training_corpus" / "train.jsonl")
    validation_first = _read_jsonl(tmp_path / "datasets" / "training_corpus" / "validation.jsonl")
    second = promote_reviewed_corpus_splits(normalized)
    train_second = _read_jsonl(tmp_path / "datasets" / "training_corpus" / "train.jsonl")
    validation_second = _read_jsonl(tmp_path / "datasets" / "training_corpus" / "validation.jsonl")
    assert first["train_rows"] == second["train_rows"]
    assert first["validation_rows"] == second["validation_rows"]
    assert train_first == train_second
    assert validation_first == validation_second

