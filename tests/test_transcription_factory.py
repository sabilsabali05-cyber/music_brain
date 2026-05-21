import pytest

from music_brain.transcription import create_transcriber
from music_brain.transcription.fake import FakeTranscriber
from music_brain.transcription.modal_client import ModalFakeTranscriber


def test_factory_accepts_fake_local_fake() -> None:
    transcriber = create_transcriber(
        provider_requested="fake",
        backend="local_fake",
        modal_endpoint=None,
    )
    assert isinstance(transcriber, FakeTranscriber)


def test_factory_accepts_fake_modal_fake() -> None:
    transcriber = create_transcriber(
        provider_requested="fake",
        backend="modal_fake",
        modal_endpoint=None,
    )
    assert isinstance(transcriber, ModalFakeTranscriber)


def test_factory_rejects_yourmt3_modal_for_now() -> None:
    with pytest.raises(NotImplementedError, match="not implemented yet"):
        create_transcriber(
            provider_requested="yourmt3",
            backend="modal",
            modal_endpoint=None,
        )
