from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

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


class BaseSymbolicModelAdapter(ABC):
    provider_id: str
    display_name: str
    default_role: str
    role_hint: str
    installation_hint: str
    capabilities: list[SymbolicModelCapability]

    def __init__(self, *, stub_mode: bool = False) -> None:
        self.stub_mode = stub_mode

    @abstractmethod
    def check_available(self) -> ModelAvailabilityReport:
        raise NotImplementedError

    @abstractmethod
    def describe_capabilities(self) -> SymbolicModelProvider:
        raise NotImplementedError

    @abstractmethod
    def generate_midi(self, request: SymbolicGenerationRequest) -> SymbolicGenerationResult:
        raise NotImplementedError

    @abstractmethod
    def score_midi(self, request: SymbolicScoringRequest) -> SymbolicScoringResult:
        raise NotImplementedError

    @abstractmethod
    def embed_midi(self, midi_path: str) -> SymbolicEmbeddingResult:
        raise NotImplementedError

    @abstractmethod
    def explain_limitations(self) -> list[str]:
        raise NotImplementedError

    def _unavailable_generation_result(
        self,
        *,
        request: SymbolicGenerationRequest,
        reason: str,
        extra_limitations: list[str] | None = None,
    ) -> SymbolicGenerationResult:
        return SymbolicGenerationResult(
            provider_id=self.provider_id,
            available=False,
            generation_status="unavailable",
            limitations=[reason] + (extra_limitations or []),
            provenance={
                "provider_id": self.provider_id,
                "task_type": request.task_type,
                "prompt": request.prompt,
                "prototype_generated_from_existing_examples": False,
                "not_original_model_composition": True,
                "not_ground_truth": True,
                "not_model_trained": True,
            },
        )

    def _unavailable_scoring_result(self, *, reason: str) -> SymbolicScoringResult:
        return SymbolicScoringResult(
            provider_id=self.provider_id,
            available=False,
            scoring_status="unavailable",
            limitations=[reason],
        )

    def _unavailable_embedding_result(self, *, reason: str) -> SymbolicEmbeddingResult:
        return SymbolicEmbeddingResult(
            provider_id=self.provider_id,
            available=False,
            embedding_status="unavailable",
            limitations=[reason],
        )

    def _provider_payload(self) -> SymbolicModelProvider:
        return SymbolicModelProvider(
            provider_id=self.provider_id,
            display_name=self.display_name,
            capabilities=list(self.capabilities),
            default_role=self.default_role,
            role_hint=self.role_hint,
            installation_hint=self.installation_hint,
        )

    def _availability_payload(self, *, available: bool, details: dict[str, Any] | None = None) -> ModelAvailabilityReport:
        return ModelAvailabilityReport(
            provider_id=self.provider_id,
            display_name=self.display_name,
            available=available,
            capabilities=list(self.capabilities),
            default_role=self.default_role,
            role_hint=self.role_hint,
            installation_hint=self.installation_hint,
            details=details or {},
            limitations=[] if available else self.explain_limitations(),
        )
