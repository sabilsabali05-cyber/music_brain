import json
import wave
from pathlib import Path

from scripts.create_test_audio import create_test_tone
from submit_track import run_submission


def test_fake_pipeline_writes_midi_and_report(monkeypatch, tmp_path: Path) -> None:
    input_wav = tmp_path / "sample.wav"
    create_test_tone(input_wav, duration_seconds=0.5)

    library_root = tmp_path / "library"
    monkeypatch.setenv("MUSIC_BRAIN_LIBRARY_ROOT", str(library_root))
    monkeypatch.setenv("MUSIC_BRAIN_PROVIDER", "fake")
    monkeypatch.setenv("MUSIC_BRAIN_BACKEND", "local_fake")

    def fake_convert_to_wav(input_path: Path, output_path: Path) -> None:
        output_path.write_bytes(input_path.read_bytes())

    monkeypatch.setattr("submit_track.convert_to_normalized_wav", fake_convert_to_wav)

    report = run_submission(input_wav)

    assert report.status == "success"
    assert report.provider_requested == "fake"
    assert report.provider_used == "fake"
    assert report.backend == "local_fake"
    assert report.model_version == "fake-transcriber-v0"
    assert report.fallback_used is False
    assert report.fallback_reason is None
    assert Path(report.artifacts.normalized_audio).exists()
    assert Path(report.artifacts.full_mix_midi).exists()
    assert Path(report.artifacts.job_report).exists()

    payload = json.loads(Path(report.artifacts.job_report).read_text(encoding="utf-8"))
    assert payload["provider_requested"] == "fake"
    assert payload["provider_used"] == "fake"
    assert payload["backend"] == "local_fake"
    assert payload["model_version"] == "fake-transcriber-v0"
    assert payload["fallback_used"] is False
    assert payload["fallback_reason"] is None
    assert payload["status"] == "success"

    with wave.open(str(Path(report.artifacts.normalized_audio)), "rb") as normalized:
        assert normalized.getnframes() > 0

