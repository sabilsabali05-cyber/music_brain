from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.make_clip import make_clip


def test_make_clip_success_with_mocked_ffmpeg(tmp_path: Path, monkeypatch) -> None:
    input_audio = tmp_path / "input.wav"
    input_audio.write_bytes(b"fake-audio")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("scripts.make_clip.shutil.which", lambda _: "ffmpeg")

    def _fake_run(command: list[str], capture_output: bool, text: bool, check: bool) -> subprocess.CompletedProcess[str]:
        assert command[0] == "ffmpeg"
        output_path = Path(command[-1])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"clip-bytes")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("scripts.make_clip.subprocess.run", _fake_run)

    clip_path = make_clip(input_audio, start=2.0, seconds=5.0)

    assert clip_path.exists()
    assert clip_path.read_bytes() == b"clip-bytes"
    assert "samples/clips" in clip_path.as_posix()


def test_make_clip_requires_ffmpeg(tmp_path: Path, monkeypatch) -> None:
    input_audio = tmp_path / "input.wav"
    input_audio.write_bytes(b"fake-audio")
    monkeypatch.setattr("scripts.make_clip.shutil.which", lambda _: None)

    try:
        make_clip(input_audio)
        assert False, "Expected RuntimeError when ffmpeg is missing"
    except RuntimeError as exc:
        assert "ffmpeg not found on PATH" in str(exc)


def test_make_clip_defaults_to_30_seconds(tmp_path: Path, monkeypatch) -> None:
    input_audio = tmp_path / "input.wav"
    input_audio.write_bytes(b"fake-audio")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("scripts.make_clip.shutil.which", lambda _: "ffmpeg")
    seen_commands: list[list[str]] = []

    def _fake_run(command: list[str], capture_output: bool, text: bool, check: bool) -> subprocess.CompletedProcess[str]:
        seen_commands.append(command)
        output_path = Path(command[-1])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"clip-bytes")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("scripts.make_clip.subprocess.run", _fake_run)

    make_clip(input_audio)

    assert seen_commands, "ffmpeg command was not invoked"
    assert "-t" in seen_commands[0]
    t_index = seen_commands[0].index("-t")
    assert seen_commands[0][t_index + 1] == "30.0"
