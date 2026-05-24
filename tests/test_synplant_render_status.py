from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_synplant_render_status_is_honest_and_redacted() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "scripts" / "generate_complete_song_wav.py"
    result = subprocess.run([sys.executable, str(script)], cwd=repo_root, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr

    status_json = repo_root / "reports" / "local_rendering" / "synplant_render_status.json"
    status_md = repo_root / "reports" / "local_rendering" / "synplant_render_status.md"
    assert status_json.exists()
    assert status_md.exists()

    payload = json.loads(status_json.read_text(encoding="utf-8"))
    for key in (
        "synplant_configured",
        "synplant_available",
        "synplant_used",
        "reaper_project_created",
        "wav_rendered",
    ):
        assert isinstance(payload[key], bool)
    assert isinstance(payload["exact_blockers"], list)

    if payload["wav_rendered"]:
        assert payload["final_wav_path"]
    else:
        assert payload["final_wav_path"] == ""
        assert payload["exact_blockers"]

    joined = status_json.read_text(encoding="utf-8") + "\n" + status_md.read_text(encoding="utf-8")
    assert "C:\\Users\\" not in joined
    assert "C:/Users/" not in joined
