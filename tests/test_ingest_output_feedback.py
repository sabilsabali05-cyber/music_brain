from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_ingest_output_feedback_blocks_unauthorized_row(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    input_path = tmp_path / "feedback.json"
    input_path.write_text(
        json.dumps(
            {
                "feedback_id": "f1",
                "generation_id": "music_understanding_loop_v1",
                "candidate_id": "candidate_01",
                "authorization_status": "restricted",
                "source_authorized_for_learning": True,
                "reviewer": "x",
                "taste_label": "like",
                "accepted": False,
                "musicality_score": 0.5,
                "groove_score": 0.5,
                "harmony_score": 0.5,
            }
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "ingest_output_feedback.py"), "--input", input_path.as_posix()],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((repo_root / "reports" / "taste_learning" / "feedback_ingestion_report.json").read_text(encoding="utf-8"))
    assert report["accepted_count"] == 0
    assert report["blocked_count"] >= 1
