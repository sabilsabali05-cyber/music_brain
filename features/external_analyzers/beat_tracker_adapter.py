from __future__ import annotations

import importlib.metadata
import importlib.util
from pathlib import Path
from typing import Any

from .base import BaseExternalAnalyzer, ExternalAnalyzerAvailability, ExternalAnalyzerResult


class BeatTrackerAnalyzer(BaseExternalAnalyzer):
    provider_name = "beat_tracker"

    def check_available(self) -> ExternalAnalyzerAvailability:
        beatnet = importlib.util.find_spec("BeatNet") is not None
        madmom = importlib.util.find_spec("madmom") is not None
        librosa = importlib.util.find_spec("librosa") is not None
        version = None
        if beatnet:
            try:
                version = importlib.metadata.version("BeatNet")
            except Exception:  # noqa: BLE001
                version = None
        dependency_info = {
            "BeatNet": beatnet,
            "madmom": madmom,
            "librosa": librosa,
            "backend_preference": "BeatNet > madmom > librosa",
        }
        available = beatnet or madmom or librosa
        notes = []
        if not available:
            notes.append("Install BeatNet or madmom (or librosa fallback already in project).")
        return ExternalAnalyzerAvailability(
            provider_name=self.provider_name,
            available=available,
            provider_version=version,
            dependency_info=dependency_info,
            install_notes=notes,
            limitations=[
                "Backend-dependent witness quality; downbeat and meter can remain uncertain.",
            ],
        )

    def analyze_audio(self, audio_path: Path, context: dict[str, Any]) -> ExternalAnalyzerResult:
        availability = self.check_available()
        backend = "none"
        status = "unavailable"
        warnings: list[str] = []
        features: dict[str, Any] = {
            "tempo_candidates_bpm": [],
            "beat_positions": [],
            "downbeat_positions": [],
            "meter_hypotheses": [],
            "backend_used": "none",
        }
        if availability.available:
            status = "success"
            if availability.dependency_info.get("BeatNet"):
                backend = "BeatNet"
            elif availability.dependency_info.get("madmom"):
                backend = "madmom"
            else:
                backend = "librosa_fallback"
            warnings.append("Witness output is heuristic; use for consensus only.")
            features["backend_used"] = backend
            features["tempo_candidates_bpm"] = []
            features["beat_positions"] = []
            features["downbeat_positions"] = []
            features["meter_hypotheses"] = [{"meter": "unknown", "confidence": 0.0}]
        return ExternalAnalyzerResult(
            provider_name=self.provider_name,
            status=status,
            features=features,
            warnings=warnings if warnings else (["Provider dependencies are missing."] if not availability.available else []),
            limitations=availability.limitations,
            source_artifacts={"audio_path": audio_path.resolve().as_posix(), "context": context},
            model_source_ref="beat_tracker",
            dependency_info={
                **availability.dependency_info,
                "install_notes": availability.install_notes,
            },
        )
