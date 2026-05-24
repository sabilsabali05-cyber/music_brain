from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_generate_ranked_midi_candidates_outputs_required_fields() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "generate_ranked_midi_candidates.py")],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report_path = repo_root / "reports" / "taste_learning" / "ranked_midi_candidates_report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["candidates_generated"] >= 8
    assert payload["policy"]["wav_rendering_attempted"] is False
    assert payload["policy"]["chordpotion_variant_created"] is False
    assert payload["selected_candidate_path"]
