from __future__ import annotations

import json
from pathlib import Path

from scripts.normalize_music_corpus_artifacts import normalize_music_corpus_artifacts


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_normalization_handles_duplicates_and_writes_reports(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "datasets" / "training_exports" / "20260522_example" / "accepted_records.jsonl",
        [
            {
                "record_id": "same_id",
                "review_status": "accepted",
                "training_allowed": True,
                "authorization_status": "accepted",
                "human_rating": 8,
                "keep_reject_label": "keep",
            },
            {
                "record_id": "same_id",
                "review_status": "accepted",
                "training_allowed": True,
                "authorization_status": "accepted",
                "human_rating": 8,
                "keep_reject_label": "keep",
            },
        ],
    )
    _write_json(
        tmp_path / "reports" / "review_queue" / "review_queue_summary.json",
        {"status": "ok", "created_at": "2026-05-22T00:00:00+00:00"},
    )

    summary = normalize_music_corpus_artifacts(tmp_path)
    assert summary["total_rows"] == 2  # includes non-row report dict + single deduped row
    assert summary["duplicate_rows"] == 1
    assert summary["schema_drift_resolved_count"] >= 1

    normalized_path = tmp_path / "datasets" / "normalized_music_corpus" / "normalized_music_corpus.jsonl"
    normalized_lines = [json.loads(line) for line in normalized_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert all("item_id" in row for row in normalized_lines)


def test_missing_policy_is_reported(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "datasets" / "review_queue" / "review_queue_v1.jsonl",
        [{"queue_id": "rq1", "authorization": "unknown"}],
    )
    summary = normalize_music_corpus_artifacts(tmp_path)
    assert summary["policy_missing_rows"] >= 1
    assert summary["training_eligible_rows"] == 0

