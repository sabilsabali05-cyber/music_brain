from __future__ import annotations

import json
from pathlib import Path

from scripts.apply_music_intelligence_schema import apply_music_intelligence_schema


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_apply_schema_builds_report_and_records(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    normalized = tmp_path / "datasets" / "normalized_music_corpus" / "normalized_music_corpus.jsonl"
    _write_jsonl(
        normalized,
        [
            {
                "item_id": "a1",
                "source_artifact": "datasets/training_exports/a.jsonl",
                "source_path_redacted": r"C:\Users\izzyo\private.mid",
                "authorization_status": "accepted",
                "training_allowed": False,
                "retrieval_allowed": True,
                "policy_status": "missing_fields",
                "keep_reject_label": "unlabeled",
                "harmony_quality": 9,
                "melody_quality": 8,
                "rhythm_quality": 8,
                "texture_quality": 8,
                "arrangement_quality": 8,
                "musicality_quality": 9,
                "human_rating": 9,
            },
            {
                "item_id": "a2",
                "source_artifact": "datasets/training_exports/b.jsonl",
                "source_path_redacted": "datasets/training_exports/b.mid",
                "authorization_status": "private",
                "training_allowed": False,
                "retrieval_allowed": False,
                "policy_status": "complete",
                "keep_reject_label": "keep",
                "harmony_quality": 2,
                "melody_quality": 2,
                "rhythm_quality": 2,
                "texture_quality": 2,
                "arrangement_quality": 2,
                "musicality_quality": 2,
                "human_rating": 2,
                "excluded_reason": "junk_noise",
            },
        ],
    )
    _write_jsonl(tmp_path / "datasets" / "training_corpus" / "review_required.jsonl", [])
    _write_jsonl(tmp_path / "datasets" / "training_corpus" / "retrieval_only.jsonl", [])
    (tmp_path / "reports" / "database").mkdir(parents=True, exist_ok=True)
    (tmp_path / "reports" / "training_corpus").mkdir(parents=True, exist_ok=True)
    (tmp_path / "reports" / "database" / "normalized_music_corpus_report.json").write_text("{}", encoding="utf-8")
    (tmp_path / "reports" / "training_corpus" / "corpus_split_report.json").write_text("{}", encoding="utf-8")

    report = apply_music_intelligence_schema(normalized)
    assert report["total_rows_processed"] == 2
    assert report["missing_policy_count"] == 1
    assert report["training_safe_count"] == 0
    assert report["retrieval_only_count"] >= 1
    assert report["excluded_count"] >= 1

    records_path = tmp_path / "datasets" / "music_intelligence" / "music_intelligence_records.jsonl"
    lines = [json.loads(line) for line in records_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 2
    assert "<PRIVATE_LOCAL_PATH>" in lines[0]["source_path_redacted"]


def test_apply_schema_has_no_training_or_cloud_calls() -> None:
    content = Path("scripts/apply_music_intelligence_schema.py").read_text(encoding="utf-8")
    assert "modal" not in content.lower()
    assert "openai" not in content.lower()
    assert "train(" not in content.lower()
