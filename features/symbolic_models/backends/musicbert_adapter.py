from __future__ import annotations

import importlib.util
import os

from features.symbolic_models.backends.base import BaseSymbolicModelAdapter
from features.symbolic_models.model_backend_schema import (
    ModelAvailabilityReport,
    SymbolicEmbeddingResult,
    SymbolicGenerationRequest,
    SymbolicGenerationResult,
    SymbolicModelCapability,
    SymbolicModelProvider,
    SymbolicScoringRequest,
    SymbolicScoringResult,
)


class MusicBertAdapter(BaseSymbolicModelAdapter):
    provider_id = "musicbert"
    display_name = "MusicBERT"
    default_role = "evaluator_understanding_witness"
    role_hint = "Use for symbolic understanding, embeddings, similarity, reranking, and evaluation."
    installation_hint = "Install optional dependencies (e.g. torch + transformers) and set MUSICBERT_MODEL_PATH."
    capabilities: list[SymbolicModelCapability] = [
        "symbolic_embedding",
        "style_classification",
        "similarity_scoring",
        "reranking",
        "accompaniment_suggestion",
        "explanation",
    ]

    def check_available(self) -> ModelAvailabilityReport:
        if self.stub_mode:
            return self._availability_payload(available=True, details={"stub_mode": True})
        has_torch = importlib.util.find_spec("torch") is not None
        has_transformers = importlib.util.find_spec("transformers") is not None
        model_path = os.environ.get("MUSICBERT_MODEL_PATH", "").strip()
        available = has_torch and has_transformers and bool(model_path)
        return self._availability_payload(
            available=available,
            details={
                "has_torch": has_torch,
                "has_transformers": has_transformers,
                "model_path_configured": bool(model_path),
            },
        )

    def describe_capabilities(self) -> SymbolicModelProvider:
        return self._provider_payload()

    def generate_midi(self, request: SymbolicGenerationRequest) -> SymbolicGenerationResult:
        availability = self.check_available()
        if not availability.available:
            return self._unavailable_generation_result(
                request=request,
                reason="MusicBERT is evaluator-first and unavailable for generation in this environment.",
            )
        return self._unavailable_generation_result(
            request=request,
            reason="MusicBERT adapter is configured as symbolic evaluator; generation is intentionally disabled.",
        )

    def score_midi(self, request: SymbolicScoringRequest) -> SymbolicScoringResult:
        availability = self.check_available()
        if not availability.available:
            return self._unavailable_scoring_result(reason="MusicBERT dependencies/model path are unavailable.")
        return SymbolicScoringResult(
            provider_id=self.provider_id,
            available=True,
            scoring_status="unimplemented_stub",
            limitations=["MusicBERT scoring backend is not wired yet."],
        )

    def embed_midi(self, midi_path: str) -> SymbolicEmbeddingResult:
        availability = self.check_available()
        if not availability.available:
            return self._unavailable_embedding_result(reason="MusicBERT dependencies/model path are unavailable.")
        return SymbolicEmbeddingResult(
            provider_id=self.provider_id,
            available=True,
            embedding_status="unimplemented_stub",
            limitations=["MusicBERT embedding backend is not wired yet."],
        )

    def explain_limitations(self) -> list[str]:
        return [
            "MusicBERT model weights are not bundled with this repository.",
            "This adapter intentionally avoids heavyweight runtime imports at module load time.",
            "Generation is disabled because MusicBERT is treated as an evaluator/understanding witness.",
        ]
