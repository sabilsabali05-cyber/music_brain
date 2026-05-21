from music_brain.transcription import create_transcriber
from music_brain.transcription.fake import FakeTranscriber
from music_brain.transcription.modal_client import ModalFakeTranscriber
from music_brain.transcription.yourmt3_modal_client import YourMT3ModalTranscriber


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


def test_factory_accepts_yourmt3_modal() -> None:
    transcriber = create_transcriber(
        provider_requested="yourmt3",
        backend="modal",
        modal_endpoint=None,
    )
    assert isinstance(transcriber, YourMT3ModalTranscriber)
