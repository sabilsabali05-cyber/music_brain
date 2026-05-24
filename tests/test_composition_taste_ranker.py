from __future__ import annotations

import json
from pathlib import Path

from features.taste_learning.composition_ranker import train_ranker


def _write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def test_ranker_uses_heuristic_below_20(tmp_path: Path) -> None:
    feedback = tmp_path / "feedback.jsonl"
    model = tmp_path / "model.json"
    rows = [
        {
            "authorization_status": "authorized",
            "source_authorized_for_learning": True,
            "taste_label": "like",
            "musicality_score": 0.7,
            "groove_score": 0.6,
            "harmony_score": 0.6,
        }
        for _ in range(5)
    ]
    _write_rows(feedback, rows)
    result = train_ranker(feedback, model)
    assert result.trained_ranker_used is False
    assert result.heuristic_ranker_used is True


def test_ranker_trains_at_20_authorized_rows(tmp_path: Path) -> None:
    feedback = tmp_path / "feedback.jsonl"
    model = tmp_path / "model.json"
    rows = []
    for idx in range(20):
        rows.append(
            {
                "authorization_status": "authorized",
                "source_authorized_for_learning": True,
                "taste_label": "love" if idx % 2 == 0 else "like",
                "musicality_score": 0.7,
                "groove_score": 0.62,
                "harmony_score": 0.65,
            }
        )
    _write_rows(feedback, rows)
    result = train_ranker(feedback, model)
    assert result.trained_ranker_used is True
    assert result.heuristic_ranker_used is False
