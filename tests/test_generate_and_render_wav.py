from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_generate_and_render_produces_midi_and_honest_status() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "scripts" / "generate_and_render_wav.py"
    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, cwd=repo_root, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    output_root = repo_root / "outputs" / "generated_wav_v1"
    assert (output_root / "full.mid").exists()
    assert (output_root / "stems").exists()
    status_payload = json.loads((output_root / "render_result.json").read_text(encoding="utf-8"))
    assert status_payload["wav_rendered"] in {True, False}
    if not status_payload["wav_rendered"]:
        assert status_payload["assisted_render_pack"] or status_payload["missing_config"]
