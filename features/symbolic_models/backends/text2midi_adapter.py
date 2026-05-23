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


class Text2MidiAdapter(BaseSymbolicModelAdapter):
    provider_id = "text2midi"
    display_name = "Text2MIDI"
    default_role = "prompt_sketch_generator"
    role_hint = "Use for text prompt to symbolic sketch generation."
    installation_hint = "Install Text2MIDI runtime and set TEXT2MIDI_MODEL_PATH."
    capabilities: list[SymbolicModelCapability] = [
        "text_to_midi",
        "controllable_generation",
        "explanation",
    ]

    def check_available(self) -> ModelAvailabilityReport:
        if self.stub_mode:
            return self._availability_payload(available=True, details={"stub_mode": True})
        has_torch = importlib.util.find_spec("torch") is not None
        has_text2midi = importlib.util.find_spec("text2midi") is not None
        model_path = os.environ.get("TEXT2MIDI_MODEL_PATH", "").strip()
        available = has_torch and has_text2midi and bool(model_path)
        return self._availability_payload(
            available=available,
            details={
                "has_torch": has_torch,
                "has_text2midi_module": has_text2midi,
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
                reason="Text2MIDI backend is unavailable in current environment.",
            )
        return SymbolicGenerationResult(
            provider_id=self.provider_id,
            available=True,
            generation_status="unimplemented_stub",
            limitations=["Text2MIDI adapter configured but runtime generation is not implemented yet."],
            provenance={
                "provider_id": self.provider_id,
                "task_type": request.task_type,
                "prompt": request.prompt,
                "not_model_trained": True,
            },
        )

    def score_midi(self, request: SymbolicScoringRequest) -> SymbolicScoringResult:
        availability = self.check_available()
        if not availability.available:
            return self._unavailable_scoring_result(reason="Text2MIDI backend is unavailable.")
        return SymbolicScoringResult(
            provider_id=self.provider_id,
            available=True,
            scoring_status="unimplemented_stub",
            limitations=["Text2MIDI scoring endpoint is not implemented."],
        )

    def embed_midi(self, midi_path: str) -> SymbolicEmbeddingResult:
        availability = self.check_available()
        if not availability.available:
            return self._unavailable_embedding_result(reason="Text2MIDI backend is unavailable.")
        return SymbolicEmbeddingResult(
            provider_id=self.provider_id,
            available=True,
            embedding_status="unimplemented_stub",
            limitations=["Text2MIDI embedding endpoint is not implemented."],
        )

    def explain_limitations(self) -> list[str]:
        return [
            "Text2MIDI weights/runtime are optional and not included in this repository.",
            "Adapter currently performs capability/availability reporting only.",
            "No model inference is executed when backend is unavailable.",
        ]
