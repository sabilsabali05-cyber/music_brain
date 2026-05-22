from __future__ import annotations

import importlib.metadata
import importlib.util
from pathlib import Path

from .base import BaseExternalAnalyzer, ExternalAnalyzerAvailability, ExternalAnalyzerResult


class OmnizartAnalyzer(BaseExternalAnalyzer):
    provider_name = "omnizart"

    def check_available(self) -> ExternalAnalyzerAvailability:
        available = importlib.util.find_spec("omnizart") is not None
        version = None
        if available:
            try:
                version = importlib.metadata.version("omnizart")
            except Exception:  # noqa: BLE001
                version = None
        return ExternalAnalyzerAvailability(
            provider_name=self.provider_name,
            available=available,
            provider_version=version,
            dependency_info={"omnizart": available, "omnizart_version": version},
            install_notes=[] if available else ["Install Omnizart only if optional witness comparison is required."],
            limitations=["Heavy provider; default behavior reports availability only."],
        )

    def analyze_audio(self, audio_path: Path, context: dict[str, object]) -> ExternalAnalyzerResult:
        availability = self.check_available()
        if not availability.available:
            return ExternalAnalyzerResult(
                provider_name=self.provider_name,
                status="unavailable",
                warnings=["Omnizart is unavailable in this environment."],
                limitations=availability.limitations,
                source_artifacts={"audio_path": audio_path.resolve().as_posix(), "context": context},
                model_source_ref="omnizart",
                dependency_info={
                    **availability.dependency_info,
                    "install_notes": availability.install_notes,
                },
            )
        return ExternalAnalyzerResult(
            provider_name=self.provider_name,
            status="skipped",
            features={"available_modules": ["music", "drum", "chord", "vocal"]},
            warnings=["Omnizart heavy analysis is not run automatically."],
            limitations=availability.limitations,
            source_artifacts={"audio_path": audio_path.resolve().as_posix(), "context": context},
            model_source_ref="omnizart",
            dependency_info=availability.dependency_info,
        )
