from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_generate_chordpotion_ready_skeleton_outputs_files() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "scripts" / "generate_chordpotion_ready_skeleton.py"
    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, cwd=repo_root, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    output_root = repo_root / "outputs" / "chordpotion_generation_v1"
    assert (output_root / "harmony_skeleton.mid").exists()
    assert (output_root / "bass.mid").exists()
    assert (output_root / "lead_guide.mid").exists()
    assert (output_root / "generation_report.md").exists()
    assert (output_root / "provenance_report.md").exists()

