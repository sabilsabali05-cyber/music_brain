import wave
from pathlib import Path

from scripts.create_test_audio import create_test_tone


def test_create_test_audio_file(tmp_path: Path) -> None:
    out = tmp_path / "samples" / "test_tone.wav"
    written = create_test_tone(out)

    assert written == out
    assert out.exists()
    assert out.stat().st_size > 44

    with wave.open(str(out), "rb") as wav_file:
        assert wav_file.getframerate() == 44100
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.getnframes() == 5 * 44100
