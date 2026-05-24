from __future__ import annotations

import json
from pathlib import Path

from scripts.build_human_review_batch import build_human_review_batch


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_human_review_batch_caps_at_50_and_has_required_questions(tmp_path: Path) -> None:
    normalized = tmp_path / "datasets" / "normalized_music_corpus" / "normalized_music_corpus.jsonl"
    rows = []
    for idx in range(60):
        rows.append(
            {
                "item_id": f"item_{idx:03d}",
                "source_artifact": "datasets/training_exports/example/review_required_records.jsonl",
                "source_type": "training_export",
                "source_path_redacted": "<PRIVATE_LOCAL_PATH>/artifact",
                "review_status": "review_required",
                "training_allowed": False,
                "policy_status": "complete",
                "review_reason": "needs human decision",
                "tags": ["dense_region"] if idx < 5 else [],
                "provenance": {"confidence": 0.8},
            }
        )
    _write_jsonl(normalized, rows)
    payload = build_human_review_batch(normalized)
    assert payload["selection_size"] <= 50
    assert len(payload["items"]) <= 50
    assert payload["items"]
    asks = payload["items"][0]["asks"]
    assert "keep_reject_retrieval_only" in asks
    assert "training_allowed" in asks
    assert "harmony_rating" in asks

