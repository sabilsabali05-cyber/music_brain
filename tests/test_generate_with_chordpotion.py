from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_generate_with_chordpotion_produces_honest_wav_status() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "scripts" / "generate_with_chordpotion.py"
    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, cwd=repo_root, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    output_root = repo_root / "outputs" / "chordpotion_generation_v1"
    payload = json.loads((output_root / "render_result.json").read_text(encoding="utf-8"))
    wav_status = (output_root / "wav_status.md").read_text(encoding="utf-8").strip()
    assert payload["wav_rendered"] in {True, False}
    if payload["wav_rendered"]:
        assert wav_status == "rendered_wav_available"
    else:
        assert wav_status == "assisted_render_pack_created"
        assert payload.get("final_wav_path", "") == ""
    assert payload["transformed_midi_captured"] is False

