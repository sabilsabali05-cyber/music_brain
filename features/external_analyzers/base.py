from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

AnalyzerStatus = Literal["success", "unavailable", "failed", "skipped"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ExternalAnalyzerAvailability:
    provider_name: str
    available: bool
    provider_version: str | None = None
    dependency_info: dict[str, Any] = field(default_factory=dict)
    install_notes: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


@dataclass
class ExternalAnalyzerResult:
    provider_name: str
    status: AnalyzerStatus
    features: dict[str, Any] = field(default_factory=dict)
    confidence: float | None = None
    warnings: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)
    source_artifacts: dict[str, Any] = field(default_factory=dict)
    model_source_ref: str | None = None
    dependency_info: dict[str, Any] = field(default_factory=dict)


class BaseExternalAnalyzer(ABC):
    provider_name: str

    @abstractmethod
    def check_available(self) -> ExternalAnalyzerAvailability:
        raise NotImplementedError

    @abstractmethod
    def analyze_audio(self, audio_path: Path, context: dict[str, Any]) -> ExternalAnalyzerResult:
        raise NotImplementedError

    def analyze_midi(self, midi_path: Path, context: dict[str, Any]) -> ExternalAnalyzerResult:
        return ExternalAnalyzerResult(
            provider_name=self.provider_name,
            status="skipped",
            warnings=["MIDI analysis is not implemented for this provider."],
            limitations=["MIDI pathway is optional and currently disabled."],
            source_artifacts={"midi_path": midi_path.resolve().as_posix(), "context": context},
        )
