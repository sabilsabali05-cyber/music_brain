import json
from pathlib import Path

from music_brain.audio import AudioProcessingError
from scripts.create_test_audio import create_test_tone
from submit_track import run_submission


def test_failure_still_writes_job_report(monkeypatch, tmp_path: Path) -> None:
    input_wav = tmp_path / "sample.wav"
    create_test_tone(input_wav, duration_seconds=0.2)

    library_root = tmp_path / "library"
    monkeypatch.setenv("MUSIC_BRAIN_LIBRARY_ROOT", str(library_root))
    monkeypatch.setenv("MUSIC_BRAIN_PROVIDER", "fake")
    monkeypatch.setenv("MUSIC_BRAIN_BACKEND", "local_fake")

    def failing_convert(_input_path: Path, _output_path: Path) -> None:
        raise AudioProcessingError("ffmpeg missing in test")

    monkeypatch.setattr("submit_track.convert_to_normalized_wav", failing_convert)

    report = run_submission(input_wav)

    assert report.status == "failed"
    assert report.error is not None
    assert report.error.stage == "ffmpeg_convert"
    assert Path(report.artifacts.job_report).exists()

    payload = json.loads(Path(report.artifacts.job_report).read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    assert payload["error"]["stage"] == "ffmpeg_convert"
    assert payload["artifacts"]["job_report"] == report.artifacts.job_report
