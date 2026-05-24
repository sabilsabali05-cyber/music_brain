from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_run_music_understanding_loop_honest_status() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "run_music_understanding_loop.py")],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode in {0, 1}
    status_path = repo_root / "reports" / "integration" / "music_understanding_loop_status.json"
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    assert payload["no_cloud_calls"] is True
    assert payload["wav_rendering_attempted"] is False
    assert payload["chordpotion_variant_created"] is False
    assert payload["candidates_generated"] >= 8
