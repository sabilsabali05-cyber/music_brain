from __future__ import annotations

from .base import BaseTranscriber
from .fake import FakeTranscriber
from .modal_client import ModalFakeTranscriber
from .yourmt3_modal_client import YourMT3ModalTranscriber


def create_transcriber(
    *,
    provider_requested: str,
    backend: str,
    modal_endpoint: str | None,
) -> BaseTranscriber:
    if backend == "local_fake" and provider_requested == "fake":
        return FakeTranscriber()

    if backend == "modal_fake" and provider_requested == "fake":
        return ModalFakeTranscriber(endpoint=modal_endpoint)

    if backend == "modal" and provider_requested == "yourmt3":
        return YourMT3ModalTranscriber(endpoint=modal_endpoint)

    raise ValueError(
        "Unsupported provider/backend combination: "
        f"provider={provider_requested}, backend={backend}. "
        "Supported: (fake, local_fake), (fake, modal_fake), (yourmt3, modal)."
    )
