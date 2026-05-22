from __future__ import annotations

import importlib
import importlib.metadata
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .base import BaseExternalAnalyzer, ExternalAnalyzerAvailability, ExternalAnalyzerResult

ESSENTIA_CLI_CANDIDATES = [
    "essentia_streaming_extractor_music",
    "essentia_streaming_extractor_freesound",
]


class EssentiaAnalyzer(BaseExternalAnalyzer):
    provider_name = "essentia"

    def _detect_python_essentia(self) -> tuple[bool, str | None, str | None]:
        spec = importlib.util.find_spec("essentia")
        if spec is None:
            return False, None, "Python package `essentia` is not installed."
        version: str | None = None
        try:
            version = importlib.metadata.version("essentia")
        except Exception:  # noqa: BLE001
            version = None
        return True, version, None

    def _detect_cli(self) -> tuple[str | None, str | None]:
        for candidate in ESSENTIA_CLI_CANDIDATES:
            binary = shutil.which(candidate)
            if binary:
                return binary, candidate
        return None, None

    def check_available(self) -> ExternalAnalyzerAvailability:
        python_available, version, python_note = self._detect_python_essentia()
        cli_path, cli_name = self._detect_cli()
        available = python_available or bool(cli_path)
        install_notes: list[str] = []
        if not available:
            install_notes.append("Install Python Essentia (pip install essentia) or Essentia CLI extractors.")
        if python_note:
            install_notes.append(python_note)
        return ExternalAnalyzerAvailability(
            provider_name=self.provider_name,
            available=available,
            provider_version=version or ("cli" if cli_path else None),
            dependency_info={
                "python_module": "essentia" if python_available else None,
                "essentia_version": version,
                "cli_executable": cli_path,
                "cli_name": cli_name,
            },
            install_notes=install_notes,
            limitations=[
                "Descriptor coverage varies by installed Essentia build and model data.",
                "Essentia licensing may require AGPL/commercial compliance review.",
            ],
        )

    def _analyze_with_python(self, audio_path: Path) -> dict[str, Any]:
        # Best-effort dynamic import to keep this provider strictly optional.
        standard = importlib.import_module("essentia.standard")
        extractor = standard.MusicExtractor()
        pool, _ = extractor(str(audio_path))
        result: dict[str, Any] = {}
        for key in pool.descriptorNames():
            try:
                value = pool[key]
                if hasattr(value, "tolist"):
                    value = value.tolist()
                result[key] = value
            except Exception:  # noqa: BLE001
                continue
        return result

    def _analyze_with_cli(self, audio_path: Path, cli_path: str) -> dict[str, Any]:
        command = [cli_path, str(audio_path), "-"]
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=240,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"Essentia CLI failed ({completed.returncode}): {completed.stderr.strip()}")
        parsed = json.loads(completed.stdout)
        if not isinstance(parsed, dict):
            raise RuntimeError("Essentia CLI output was not a JSON object.")
        return parsed

    def analyze_audio(self, audio_path: Path, context: dict[str, Any]) -> ExternalAnalyzerResult:
        availability = self.check_available()
        if not availability.available:
            return ExternalAnalyzerResult(
                provider_name=self.provider_name,
                status="unavailable",
                warnings=["Essentia is unavailable in this environment."],
                limitations=availability.limitations,
                source_artifacts={"audio_path": audio_path.resolve().as_posix(), "context": context},
                model_source_ref="essentia",
                dependency_info={
                    **availability.dependency_info,
                    "install_notes": availability.install_notes,
                },
            )

        audio_descriptors: dict[str, Any] = {}
        warnings: list[str] = []
        try:
            if availability.dependency_info.get("python_module"):
                raw = self._analyze_with_python(audio_path)
            else:
                cli_path = str(availability.dependency_info.get("cli_executable") or "")
                raw = self._analyze_with_cli(audio_path, cli_path)
        except Exception as exc:  # noqa: BLE001
            return ExternalAnalyzerResult(
                provider_name=self.provider_name,
                status="failed",
                warnings=[f"Essentia execution failed: {exc}"],
                limitations=availability.limitations,
                source_artifacts={"audio_path": audio_path.resolve().as_posix(), "context": context},
                model_source_ref="essentia",
                dependency_info=availability.dependency_info,
            )

        for key, value in raw.items():
            audio_descriptors[str(key)] = value
        return ExternalAnalyzerResult(
            provider_name=self.provider_name,
            status="success",
            features={
                "audio_descriptors": audio_descriptors,
                "rhythm_descriptors": {k: v for k, v in audio_descriptors.items() if "rhythm" in k.lower() or "tempo" in k.lower()},
                "tonal_descriptors": {k: v for k, v in audio_descriptors.items() if "tonal" in k.lower() or "key" in k.lower()},
                "spectral_descriptors": {k: v for k, v in audio_descriptors.items() if "spectral" in k.lower()},
                "high_level_descriptors": {k: v for k, v in audio_descriptors.items() if "mood" in k.lower() or "danceability" in k.lower()},
                "model_outputs": {k: v for k, v in audio_descriptors.items() if "model" in k.lower() or "classifier" in k.lower()},
            },
            warnings=warnings,
            limitations=availability.limitations,
            source_artifacts={"audio_path": audio_path.resolve().as_posix(), "context": context},
            model_source_ref="essentia",
            dependency_info=availability.dependency_info,
        )
