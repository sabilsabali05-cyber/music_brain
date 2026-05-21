from pathlib import Path

from music_brain.transcription.base import TranscriptionRequest
from music_brain.transcription.modal_client import ModalFakeTranscriber


def test_modal_client_writes_midi_from_mocked_remote(tmp_path: Path) -> None:
    normalized = tmp_path / "normalized.wav"
    normalized.write_bytes(b"RIFFfakewav")
    output_midi = tmp_path / "out.mid"

    def fake_remote_call(_audio_bytes: bytes) -> dict[str, object]:
        return {
            "midi_bytes": b"MThd\x00\x00\x00\x06\x00\x00\x00\x01\x01\xe0MTrk\x00\x00\x00\x04\x00\xff/\x00",
            "provider_used": "fake",
            "backend": "modal_fake",
            "model_version": "modal-fake-transcriber-v0",
        }

    transcriber = ModalFakeTranscriber(endpoint=None, remote_call=fake_remote_call)
    result = transcriber.transcribe(
        TranscriptionRequest(
            track_id="trk_test",
            normalized_audio_path=normalized,
            output_midi_path=output_midi,
        )
    )

    assert output_midi.exists()
    assert result.provider_used == "fake"
    assert result.backend == "modal_fake"
    assert result.model_version == "modal-fake-transcriber-v0"
    assert result.fallback_used is False
    assert result.fallback_reason is None
