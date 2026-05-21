from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast


ProviderRequested = Literal["fake", "mt3", "yourmt3"]
Backend = Literal["local_fake", "modal_fake", "modal"]


@dataclass(frozen=True)
class AppConfig:
    library_root: Path
    provider_requested: ProviderRequested
    backend: Backend
    modal_endpoint: str | None


def load_config() -> AppConfig:
    provider = os.getenv("MUSIC_BRAIN_PROVIDER", "fake").strip().lower()
    backend = os.getenv("MUSIC_BRAIN_BACKEND", "local_fake").strip().lower()

    allowed_providers = {"fake", "mt3", "yourmt3"}
    allowed_backends = {"local_fake", "modal_fake", "modal"}
    if provider not in allowed_providers:
        raise ValueError(
            f"Invalid MUSIC_BRAIN_PROVIDER={provider!r}. "
            f"Allowed: {sorted(allowed_providers)}"
        )
    if backend not in allowed_backends:
        raise ValueError(
            f"Invalid MUSIC_BRAIN_BACKEND={backend!r}. "
            f"Allowed: {sorted(allowed_backends)}"
        )

    return AppConfig(
        library_root=Path(os.getenv("MUSIC_BRAIN_LIBRARY_ROOT", "library")),
        provider_requested=cast(ProviderRequested, provider),
        backend=cast(Backend, backend),
        modal_endpoint=os.getenv("MUSIC_BRAIN_MODAL_ENDPOINT"),
    )
