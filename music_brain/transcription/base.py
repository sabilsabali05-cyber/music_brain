from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class TranscriptionRequest:
    track_id: str
    normalized_audio_path: Path
    output_midi_path: Path


@dataclass(frozen=True)
class TranscriptionResult:
    provider_used: Literal["fake", "mt3", "yourmt3", "none"]
    backend: Literal["local_fake", "modal_fake", "modal"]
    model_version: str
    fallback_used: bool
    fallback_reason: str | None


class BaseTranscriber(ABC):
    @abstractmethod
    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        """Transcribe normalized WAV into MIDI."""
