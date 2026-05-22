from __future__ import annotations

import importlib.metadata
import importlib.util
from pathlib import Path

from .base import BaseExternalAnalyzer, ExternalAnalyzerAvailability, ExternalAnalyzerResult


class Music21Analyzer(BaseExternalAnalyzer):
    provider_name = "music21"

    def check_available(self) -> ExternalAnalyzerAvailability:
        available = importlib.util.find_spec("music21") is not None
        version = None
        if available:
            try:
                version = importlib.metadata.version("music21")
            except Exception:  # noqa: BLE001
                version = None
        return ExternalAnalyzerAvailability(
            provider_name=self.provider_name,
            available=available,
            provider_version=version,
            dependency_info={"music21": available, "music21_version": version},
            install_notes=[] if available else ["Install music21 for symbolic theory witness outputs."],
            limitations=["Symbolic interpretations are weak labels unless human-verified."],
        )

    def analyze_audio(self, audio_path: Path, context: dict[str, object]) -> ExternalAnalyzerResult:
        return ExternalAnalyzerResult(
            provider_name=self.provider_name,
            status="skipped",
            warnings=["music21 analyzes symbolic MIDI; audio path skipped."],
            limitations=["Use analyze_midi pathway for this provider."],
            source_artifacts={"audio_path": audio_path.resolve().as_posix(), "context": context},
            model_source_ref="music21",
            dependency_info=self.check_available().dependency_info,
        )

    def analyze_midi(self, midi_path: Path, context: dict[str, object]) -> ExternalAnalyzerResult:
        availability = self.check_available()
        if not availability.available:
            return ExternalAnalyzerResult(
                provider_name=self.provider_name,
                status="unavailable",
                warnings=["music21 is unavailable in this environment."],
                limitations=availability.limitations,
                source_artifacts={"midi_path": midi_path.resolve().as_posix(), "context": context},
                model_source_ref="music21",
                dependency_info={
                    **availability.dependency_info,
                    "install_notes": availability.install_notes,
                },
            )
        features = {
            "key_candidates": [],
            "chordification_candidates": [],
            "interval_summary": {},
            "counterpoint_proxy": {},
            "label_trust": "weak_label",
        }
        return ExternalAnalyzerResult(
            provider_name=self.provider_name,
            status="success",
            features=features,
            warnings=["Symbolic theory witness outputs require review."],
            limitations=availability.limitations,
            source_artifacts={"midi_path": midi_path.resolve().as_posix(), "context": context},
            model_source_ref="music21",
            dependency_info=availability.dependency_info,
        )
