from __future__ import annotations

import json

from features.beat_battle_agent.battle_draft_ranker import rank_round_drafts


def test_battle_draft_ranker_outputs_selected_submission(tmp_path) -> None:
    candidates_path = tmp_path / "outputs" / "beat_battle_agent" / "R1" / "ranked" / "draft_candidates.json"
    candidates_path.parent.mkdir(parents=True, exist_ok=True)
    candidates_path.write_text(
        json.dumps(
            [
                {"draft_id": "d1", "ranker_input_score": 0.7},
                {"draft_id": "d2", "ranker_input_score": 0.9},
            ]
        ),
        encoding="utf-8",
    )
    report = rank_round_drafts(tmp_path, "R1")
    assert report["ranked_count"] == 2
    assert "selected_submission.json" in report["selected_submission_path"]
