from __future__ import annotations

import json
from pathlib import Path

from scripts.build_music_intelligence_review_form import build_music_intelligence_review_form


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_review_batch_prioritizes_high_value_near_eligible(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    records = tmp_path / "datasets" / "music_intelligence" / "music_intelligence_records.jsonl"
    _write_jsonl(
        records,
        [
            {
                "item_id": "high_value",
                "source_artifact": "datasets/x.jsonl",
                "source_path_redacted": "datasets/x.mid",
                "scores": {"retrieval_value_score": 0.95, "training_value_score": 0.80},
                "promotion_decision": {"promotion_label": "retrieval_only", "blockers": ["policy_fields_incomplete"]},
            },
            {
                "item_id": "low_value",
                "source_artifact": "datasets/y.jsonl",
                "source_path_redacted": "datasets/y.mid",
                "scores": {"retrieval_value_score": 0.30, "training_value_score": 0.10},
                "promotion_decision": {"promotion_label": "retrieval_only", "blockers": ["many"]},
            },
            {
                "item_id": "already_training_safe",
                "source_artifact": "datasets/z.jsonl",
                "source_path_redacted": "datasets/z.mid",
                "scores": {"retrieval_value_score": 0.99, "training_value_score": 0.99},
                "promotion_decision": {"promotion_label": "training_safe", "blockers": []},
            },
        ],
    )

    payload = build_music_intelligence_review_form(records)
    assert payload["selection_size"] == 2
    assert payload["items"][0]["item_id"] == "high_value"
    assert payload["items"][0]["questions"][0] == "is this musically valuable?"


def test_review_form_has_exact_question_set() -> None:
    content = Path("scripts/build_music_intelligence_review_form.py").read_text(encoding="utf-8")
    required = [
        "is this musically valuable?",
        "best time range",
        "junk/noisy time range",
        "harmony quality 1-10",
        "chord movement quality 1-10",
        "bass movement quality 1-10",
        "melodic contour quality 1-10",
        "motif usefulness 1-10",
        "rhythm/groove quality 1-10",
        "texture usefulness 1-10",
        "emotional value 1-10",
        "weirdness good/bad/neutral",
        "training policy: training_safe/retrieval_only/excluded/unsure",
        "reason",
        "tags",
        "notes",
    ]
    for question in required:
        assert question in content
