from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_generate_with_intelligent_chordpotion_honest_outputs() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "generate_with_intelligent_chordpotion.py")],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    output_root = repo_root / "outputs" / "intelligent_chordpotion_generation_v1"
    selected = json.loads((output_root / "selected_chordpotion_preset.json").read_text(encoding="utf-8"))
    assert selected["selector_mode"] in {"heuristic_selector", "feedback_ranker_selector", "trained_selector"}
    assert selected["trained_selector_used"] in {True, False}
    assert selected["wav_rendered"] is False
    assert (output_root / "wav_status.md").read_text(encoding="utf-8").strip() in {"assisted_pack_created", "render_failed"}
