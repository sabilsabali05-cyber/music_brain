from __future__ import annotations

import wave
from pathlib import Path

from features.local_rendering.wav_verifier import verify_wav_file


def test_wav_verifier_missing_file(tmp_path: Path) -> None:
    result = verify_wav_file(tmp_path / "missing.wav")
    assert result.exists is False
    assert result.readable is False


def test_wav_verifier_valid_wav(tmp_path: Path) -> None:
    path = tmp_path / "ok.wav"
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(44100)
        wav.writeframes(b"\x01\x00" * 4410)
    result = verify_wav_file(path)
    assert result.exists is True
    assert result.readable is True
    assert result.duration_seconds > 0
    assert result.nonzero_samples is True
