from __future__ import annotations

from .base import BaseTranscriber
from .fake import FakeTranscriber
from .modal_client import ModalFakeTranscriber


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
        raise NotImplementedError(
            "provider=yourmt3 with backend=modal is not implemented yet. "
            "Use provider=fake and backend=modal_fake to validate remote plumbing."
        )

    raise ValueError(
        "Unsupported provider/backend combination: "
        f"provider={provider_requested}, backend={backend}. "
        "Supported now: (fake, local_fake) and (fake, modal_fake)."
    )
