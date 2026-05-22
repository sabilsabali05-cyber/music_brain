from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import BaseExternalAnalyzer, ExternalAnalyzerAvailability, ExternalAnalyzerResult
from .beat_tracker_adapter import BeatTrackerAnalyzer
from .essentia_adapter import EssentiaAnalyzer
from .music21_adapter import Music21Analyzer
from .musicnn_adapter import MusicnnAnalyzer
from .omnizart_adapter import OmnizartAnalyzer


def _provider_instances() -> dict[str, BaseExternalAnalyzer]:
    return {
        "essentia": EssentiaAnalyzer(),
        "musicnn": MusicnnAnalyzer(),
        "beat_tracker": BeatTrackerAnalyzer(),
        "music21": Music21Analyzer(),
        "omnizart": OmnizartAnalyzer(),
    }


def list_external_analyzers() -> list[str]:
    return list(_provider_instances().keys())


def check_external_analyzers() -> list[ExternalAnalyzerAvailability]:
    output: list[ExternalAnalyzerAvailability] = []
    for name, provider in _provider_instances().items():
        try:
            output.append(provider.check_available())
        except Exception as exc:  # noqa: BLE001
            output.append(
                ExternalAnalyzerAvailability(
                    provider_name=name,
                    available=False,
                    install_notes=[f"Provider check failed: {exc}"],
                    limitations=["Provider check raised an exception."],
                )
            )
    return output


def run_external_analyzers(
    audio_path: Path,
    context: dict[str, Any],
    selected: list[str] | None = None,
    midi_path: Path | None = None,
) -> list[ExternalAnalyzerResult]:
    selected_set = {item.strip().lower() for item in selected or [] if item.strip()}
    providers = _provider_instances()
    results: list[ExternalAnalyzerResult] = []
    for name, provider in providers.items():
        if selected_set and name not in selected_set:
            results.append(
                ExternalAnalyzerResult(
                    provider_name=name,
                    status="skipped",
                    warnings=["Provider not selected for this run."],
                    source_artifacts={"audio_path": audio_path.resolve().as_posix(), "context": context},
                )
            )
            continue

        availability = provider.check_available()
        if not availability.available:
            results.append(
                ExternalAnalyzerResult(
                    provider_name=name,
                    status="unavailable",
                    warnings=["Provider dependencies are missing."],
                    limitations=availability.limitations,
                    source_artifacts={"audio_path": audio_path.resolve().as_posix(), "context": context},
                    dependency_info={
                        **availability.dependency_info,
                        "install_notes": availability.install_notes,
                    },
                )
            )
            continue
        try:
            if name == "music21" and midi_path and midi_path.exists():
                results.append(provider.analyze_midi(midi_path, context))
            else:
                results.append(provider.analyze_audio(audio_path, context))
        except Exception as exc:  # noqa: BLE001
            results.append(
                ExternalAnalyzerResult(
                    provider_name=name,
                    status="failed",
                    warnings=[f"Unhandled provider error: {exc}"],
                    limitations=availability.limitations,
                    source_artifacts={"audio_path": audio_path.resolve().as_posix(), "context": context},
                    dependency_info=availability.dependency_info,
                )
            )
    return results
