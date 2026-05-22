from __future__ import annotations

import importlib
import importlib.metadata
import importlib.util
from pathlib import Path
from statistics import mean
from typing import Any

from .base import BaseExternalAnalyzer, ExternalAnalyzerAvailability, ExternalAnalyzerResult


class MusicnnAnalyzer(BaseExternalAnalyzer):
    provider_name = "musicnn"

    def check_available(self) -> ExternalAnalyzerAvailability:
        spec = importlib.util.find_spec("musicnn")
        available = spec is not None
        version: str | None = None
        if available:
            try:
                version = importlib.metadata.version("musicnn")
            except Exception:  # noqa: BLE001
                version = None
        install_notes: list[str] = []
        if not available:
            install_notes.append("Install musicnn locally (pip install musicnn).")
        return ExternalAnalyzerAvailability(
            provider_name=self.provider_name,
            available=available,
            provider_version=version,
            dependency_info={"python_module": "musicnn" if available else None, "musicnn_version": version},
            install_notes=install_notes,
            limitations=[
                "Tag outputs are model-dependent and should be treated as witness signals.",
                "Embeddings are summarized only; full vectors are intentionally omitted.",
            ],
        )

    def _embedding_summary(self, embedding: Any) -> dict[str, Any]:
        if embedding is None:
            return {}
        values: list[float] = []
        if hasattr(embedding, "flatten"):
            try:
                values = [float(item) for item in embedding.flatten().tolist()]
            except Exception:  # noqa: BLE001
                values = []
        elif isinstance(embedding, list):
            for item in embedding:
                try:
                    values.append(float(item))
                except Exception:  # noqa: BLE001
                    continue
        if not values:
            return {}
        return {
            "dimension": len(values),
            "mean": round(float(mean(values)), 6),
            "min": round(float(min(values)), 6),
            "max": round(float(max(values)), 6),
        }

    def analyze_audio(self, audio_path: Path, context: dict[str, Any]) -> ExternalAnalyzerResult:
        availability = self.check_available()
        if not availability.available:
            return ExternalAnalyzerResult(
                provider_name=self.provider_name,
                status="unavailable",
                warnings=["musicnn is unavailable in this environment."],
                limitations=availability.limitations,
                source_artifacts={"audio_path": audio_path.resolve().as_posix(), "context": context},
                model_source_ref="musicnn",
                dependency_info={
                    **availability.dependency_info,
                    "install_notes": availability.install_notes,
                },
            )

        try:
            extractor_mod = importlib.import_module("musicnn.extractor")
            extractor = getattr(extractor_mod, "extractor")
            output = extractor(str(audio_path), model="MSD_musicnn", extract_features=True)
        except Exception as exc:  # noqa: BLE001
            return ExternalAnalyzerResult(
                provider_name=self.provider_name,
                status="failed",
                warnings=[f"musicnn execution failed: {exc}"],
                limitations=availability.limitations,
                source_artifacts={"audio_path": audio_path.resolve().as_posix(), "context": context},
                model_source_ref="musicnn",
                dependency_info=availability.dependency_info,
            )

        # musicnn return signatures vary by version; parse defensively.
        tags: list[str] = []
        scores: dict[str, float] = {}
        embedding_summary: dict[str, Any] = {}
        model_info: dict[str, Any] = {"model_name": "MSD_musicnn"}

        if isinstance(output, tuple) and len(output) >= 2:
            maybe_tags = output[0]
            maybe_scores = output[1]
            maybe_embedding = output[2] if len(output) > 2 else None
            if isinstance(maybe_tags, list):
                tags = [str(item) for item in maybe_tags]
            if isinstance(maybe_scores, list):
                for idx, value in enumerate(maybe_scores):
                    if idx >= len(tags):
                        break
                    try:
                        scores[tags[idx]] = round(float(value), 6)
                    except Exception:  # noqa: BLE001
                        continue
            embedding_summary = self._embedding_summary(maybe_embedding)

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        top_tags = [name for name, _ in ranked[:10]]
        return ExternalAnalyzerResult(
            provider_name=self.provider_name,
            status="success",
            features={
                "top_tags": top_tags,
                "tag_scores": {name: score for name, score in ranked[:20]},
                "embedding_reference": None,
                "embedding_summary": embedding_summary,
                "model_info": model_info,
            },
            confidence=ranked[0][1] if ranked else None,
            warnings=[],
            limitations=availability.limitations,
            source_artifacts={"audio_path": audio_path.resolve().as_posix(), "context": context},
            model_source_ref="musicnn",
            dependency_info=availability.dependency_info,
        )
