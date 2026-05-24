from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_train_selector_uses_heuristic_below_20_rows() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "train_chordpotion_preset_selector.py")],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    model_path = repo_root / "artifacts" / "model_training" / "chordpotion_preset_selector" / "model.json"
    payload = json.loads(model_path.read_text(encoding="utf-8"))
    assert payload["heuristic_or_trained"] == "heuristic_baseline"
