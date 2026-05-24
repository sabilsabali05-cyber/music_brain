from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_render_chordpotion_with_reaper_safe_fails_without_config() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "generate_chordpotion_ready_skeleton.py")],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )
    subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "build_chordpotion_transform_plan.py")],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )
    result = subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "render_chordpotion_with_reaper.py")],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads((repo_root / "outputs" / "chordpotion_generation_v1" / "render_result.json").read_text(encoding="utf-8"))
    assert payload["wav_rendered"] is False
    assert payload["transformed_midi_captured"] is False
    assert payload["missing_config"]

