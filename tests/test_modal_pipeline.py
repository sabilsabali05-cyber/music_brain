import json
from pathlib import Path

from music_brain.transcription.modal_client import ModalFakeTranscriber
from scripts.create_test_audio import create_test_tone
from submit_track import run_submission


def test_job_report_records_modal_fake(monkeypatch, tmp_path: Path) -> None:
    input_wav = tmp_path / "sample.wav"
    create_test_tone(input_wav, duration_seconds=0.3)

    library_root = tmp_path / "library"
    monkeypatch.setenv("MUSIC_BRAIN_LIBRARY_ROOT", str(library_root))
    monkeypatch.setenv("MUSIC_BRAIN_PROVIDER", "fake")
    monkeypatch.setenv("MUSIC_BRAIN_BACKEND", "modal_fake")

    def fake_convert_to_wav(input_path: Path, output_path: Path) -> None:
        output_path.write_bytes(input_path.read_bytes())

    def fake_remote_call(_audio_bytes: bytes) -> dict[str, object]:
        return {
            "midi_bytes": b"MThd\x00\x00\x00\x06\x00\x00\x00\x01\x01\xe0MTrk\x00\x00\x00\x04\x00\xff/\x00",
            "provider_used": "fake",
            "backend": "modal_fake",
            "model_version": "modal-fake-transcriber-v0",
        }

    monkeypatch.setattr("submit_track.convert_to_normalized_wav", fake_convert_to_wav)
    monkeypatch.setattr(
        "submit_track.create_transcriber",
        lambda **_kwargs: ModalFakeTranscriber(endpoint=None, remote_call=fake_remote_call),
    )

    report = run_submission(input_wav)
    payload = json.loads(Path(report.artifacts.job_report).read_text(encoding="utf-8"))

    assert report.status == "success"
    assert payload["provider_requested"] == "fake"
    assert payload["provider_used"] == "fake"
    assert payload["backend"] == "modal_fake"
    assert payload["model_version"] == "modal-fake-transcriber-v0"
    assert payload["fallback_used"] is False
    assert payload["fallback_reason"] is None
