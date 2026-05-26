from __future__ import annotations

import subprocess
from pathlib import Path


def test_no_raw_audio_files_are_tracked() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(["git", "ls-files"], cwd=repo_root, capture_output=True, text=True, check=False)
    assert result.returncode == 0
    tracked = [line.strip().lower() for line in result.stdout.splitlines() if line.strip()]
    audio_exts = (".wav", ".mp3", ".flac", ".m4a", ".aif", ".aiff")
    leaked = [path for path in tracked if path.endswith(audio_exts)]
    assert leaked == []
