from __future__ import annotations

import subprocess
from pathlib import Path


def _run_debug_args(*task_args: str) -> str:
    repo_root = Path(__file__).resolve().parents[1]
    dev_cmd = repo_root / "scripts" / "dev.cmd"
    result = subprocess.run(
        [str(dev_cmd), "debug-args", *task_args],
        capture_output=True,
        text=True,
        check=False,
        cwd=repo_root,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return result.stdout


def test_dev_runner_accepts_quoted_path_with_spaces_and_seconds() -> None:
    output = _run_debug_args(
        "clip-and-transcribe-yourmt3",
        r"C:\Users\izzyo\Downloads\Varud - Sigur Ros (Valtari).mp3",
        "30",
    )
    assert "TASK_ARG_COUNT=3" in output
    assert "TASK_ARG_1=C:\\Users\\izzyo\\Downloads\\Varud - Sigur Ros (Valtari).mp3" in output
    assert "TASK_ARG_2=30" in output


def test_dev_runner_optional_seconds_can_be_omitted() -> None:
    output = _run_debug_args(
        "clip-and-transcribe-yourmt3",
        r"C:\Users\izzyo\Downloads\Varud - Sigur Ros (Valtari).mp3",
    )
    assert "TASK_ARG_COUNT=2" in output


def test_dev_runner_commit_message_with_spaces_is_single_argument() -> None:
    output = _run_debug_args("commit-checkpoint", "Fix dev runner argument parsing")
    assert "TASK_ARG_COUNT=2" in output
    assert "TASK_ARG_0=commit-checkpoint" in output
    assert "TASK_ARG_1=Fix dev runner argument parsing" in output


def test_dev_runner_segment_audio_quoted_windows_path() -> None:
    output = _run_debug_args(
        "segment-audio",
        r"C:\Users\izzyo\Downloads\Varud - Sigur Ros (Valtari).mp3",
        "60",
    )
    assert "TASK_ARG_COUNT=3" in output
    assert "TASK_ARG_0=segment-audio" in output
    assert "TASK_ARG_1=C:\\Users\\izzyo\\Downloads\\Varud - Sigur Ros (Valtari).mp3" in output
    assert "TASK_ARG_2=60" in output
