import json
from pathlib import Path

from music_brain.transcription.yourmt3_modal_client import YourMT3ModalTranscriber
from scripts.create_test_audio import create_test_tone
from submit_track import run_submission


def test_job_report_records_yourmt3_modal(monkeypatch, tmp_path: Path) -> None:
    input_wav = tmp_path / "sample.wav"
    create_test_tone(input_wav, duration_seconds=0.25)

    library_root = tmp_path / "library"
    monkeypatch.setenv("MUSIC_BRAIN_LIBRARY_ROOT", str(library_root))
    monkeypatch.setenv("MUSIC_BRAIN_PROVIDER", "yourmt3")
    monkeypatch.setenv("MUSIC_BRAIN_BACKEND", "modal")

    def fake_convert_to_wav(input_path: Path, output_path: Path) -> None:
        output_path.write_bytes(input_path.read_bytes())

    def fake_remote_call(_audio_bytes: bytes) -> dict[str, object]:
        return {
            "midi_bytes": b"MThd\x00\x00\x00\x06\x00\x00\x00\x01\x01\xe0MTrk\x00\x00\x00\x04\x00\xff/\x00",
            "provider_used": "yourmt3",
            "backend": "modal",
            "model_version": "yourmt3-modal-experimental-v0",
            "timing": {"transcription_seconds": 0.12},
        }

    monkeypatch.setattr("submit_track.convert_to_normalized_wav", fake_convert_to_wav)
    monkeypatch.setattr(
        "submit_track.create_transcriber",
        lambda **_kwargs: YourMT3ModalTranscriber(endpoint=None, remote_call=fake_remote_call),
    )

    report = run_submission(input_wav)
    payload = json.loads(Path(report.artifacts.job_report).read_text(encoding="utf-8"))

    assert report.status == "success"
    assert payload["provider_requested"] == "yourmt3"
    assert payload["provider_used"] == "yourmt3"
    assert payload["backend"] == "modal"
    assert payload["model_version"] == "yourmt3-modal-experimental-v0"
    assert payload["fallback_used"] is False
    assert payload["fallback_reason"] is None
    assert payload["latency_seconds"]["transcription"] >= 0.0


def test_yourmt3_failure_writes_failed_job_report(monkeypatch, tmp_path: Path) -> None:
    input_wav = tmp_path / "sample.wav"
    create_test_tone(input_wav, duration_seconds=0.2)

    library_root = tmp_path / "library"
    monkeypatch.setenv("MUSIC_BRAIN_LIBRARY_ROOT", str(library_root))
    monkeypatch.setenv("MUSIC_BRAIN_PROVIDER", "yourmt3")
    monkeypatch.setenv("MUSIC_BRAIN_BACKEND", "modal")

    def fake_convert_to_wav(input_path: Path, output_path: Path) -> None:
        output_path.write_bytes(input_path.read_bytes())

    def failing_remote_call(_audio_bytes: bytes) -> dict[str, object]:
        raise RuntimeError("YourMT3 inference crash")

    monkeypatch.setattr("submit_track.convert_to_normalized_wav", fake_convert_to_wav)
    monkeypatch.setattr(
        "submit_track.create_transcriber",
        lambda **_kwargs: YourMT3ModalTranscriber(endpoint=None, remote_call=failing_remote_call),
    )

    report = run_submission(input_wav)
    payload = json.loads(Path(report.artifacts.job_report).read_text(encoding="utf-8"))

    assert report.status == "failed"
    assert payload["status"] == "failed"
    assert payload["provider_used"] == "none"
    assert payload["backend"] == "modal"
    assert payload["error"]["stage"] == "transcription"
    assert "YourMT3 inference crash" in payload["error"]["message"]
