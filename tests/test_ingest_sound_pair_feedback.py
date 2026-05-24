from __future__ import annotations

import json
from pathlib import Path

from scripts.ingest_sound_pair_feedback import run_feedback_ingestion


def test_ingest_feedback_safe_fails_without_local_notes(tmp_path: Path) -> None:
    payload = run_feedback_ingestion(tmp_path)
    assert payload["feedback_ready"] is False
    assert "missing_review_notes_local_json" in payload["blockers"]


def test_ingest_feedback_writes_required_datasets(tmp_path: Path) -> None:
    review_path = tmp_path / "local_battle_records" / "round_001" / "review_notes.local.json"
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(
        json.dumps(
            {
                "reviews": [
                    {
                        "sound_pair_id": "manual_001_synplant_001",
                        "winner": "provided",
                        "preserve_character_score": 4,
                        "uniqueness_score": 3,
                        "mix_ready": True,
                        "notes": "usable",
                    }
                ]
            },
            indent=2,
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )

    payload = run_feedback_ingestion(tmp_path)
    assert payload["feedback_ready"] is True
    assert payload["accepted_feedback_count"] == 1
    synplant_feedback = tmp_path / "datasets" / "beat_battle_agent" / "synplant_variation_feedback.jsonl"
    sound_design_feedback = tmp_path / "datasets" / "taste_learning" / "sound_design_feedback.jsonl"
    assert synplant_feedback.exists()
    assert sound_design_feedback.exists()
