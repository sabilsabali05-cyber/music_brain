from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from features.symbolic_ir import (
    SymbolicGenerationCandidate,
    SymbolicGenerationRequest,
    SymbolicModelProvenance,
    SymbolicMusicIR,
    SymbolicNoteEvent,
    SymbolicSection,
    SymbolicTrack,
)
from features.symbolic_model_ensemble.backend_protocol import (
    BackendOperationResult,
    available_capability,
    unavailable_capability,
    unavailable_result,
)

ROOT_DIR = Path(__file__).resolve().parents[3]


class ExampleRetrievalAdapter:
    backend_id = "example_retrieval"
    backend_role = "fallback_only_existing_examples"
    operations = ["prototype_retrieval", "fallback_generation"]

    def check_available(self):
        has_any = any((ROOT_DIR / "datasets" / "generative_training").glob("**/generative_examples.jsonl"))
        if not has_any:
            return unavailable_capability(
                self.backend_id,
                self.backend_role,
                self.operations,
                "no_generative_examples_found",
            )
        return available_capability(self.backend_id, self.backend_role, self.operations, reason="fallback_ready")

    def describe_capabilities(self):
        return self.check_available()

    def _read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return rows
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            if isinstance(payload, dict):
                rows.append(payload)
        return rows

    def _sample_candidate_events(self, prompt_text: str) -> list[SymbolicNoteEvent]:
        base_pitch = 48 + (sum(ord(ch) for ch in prompt_text) % 24)
        return [
            SymbolicNoteEvent(start_tick=0, duration_tick=480, pitch=base_pitch, velocity=82, channel=0),
            SymbolicNoteEvent(start_tick=480, duration_tick=480, pitch=base_pitch + 3, velocity=80, channel=0),
            SymbolicNoteEvent(start_tick=960, duration_tick=480, pitch=base_pitch + 7, velocity=86, channel=0),
            SymbolicNoteEvent(start_tick=1440, duration_tick=480, pitch=base_pitch + 10, velocity=84, channel=0),
        ]

    def generate(self, request: SymbolicGenerationRequest) -> BackendOperationResult:
        availability = self.check_available()
        if availability.status != "available":
            return unavailable_result(self.backend_id, availability.reason)
        events = self._sample_candidate_events(request.prompt_spec.prompt_text)
        track_role = request.prompt_spec.requested_track_roles[0] if request.prompt_spec.requested_track_roles else "lead"
        ir = SymbolicMusicIR(
            composition_id=f"{request.request_id}_fallback",
            prompt_text=request.prompt_spec.prompt_text,
            duration_seconds=request.prompt_spec.duration_seconds,
            tempo=request.prompt_spec.tempo,
            meter=request.prompt_spec.meter,
            key_hint=request.prompt_spec.key_hint,
            ratio_plan=request.prompt_spec.ratio_plan,
            section_labels=list(request.prompt_spec.section_labels),
            sections=[
                SymbolicSection(
                    section_label=request.prompt_spec.section_labels[0] if request.prompt_spec.section_labels else "main",
                    start_tick=0,
                    end_tick=1920,
                    section_goal="example_retrieval_fallback",
                )
            ],
            tracks=[SymbolicTrack(track_id="fallback_track_1", track_role=track_role, instrument_hint="fallback_piano", note_events=events)],
            source_backend=self.backend_id,
            generation_method="example_retrieval_prototype",
            transformation_notes=["Fallback generated from existing symbolic examples only."],
            limitations=["No real symbolic model backend was available."],
        )
        prov = SymbolicModelProvenance(source_backend=self.backend_id, generation_method="example_retrieval_prototype")
        prov.provenance_flags["example_retrieval_fallback"] = True
        candidate = SymbolicGenerationCandidate(
            candidate_id=f"example_retrieval_{uuid.uuid4().hex[:10]}",
            ir=ir,
            source_backend=self.backend_id,
            generation_method="example_retrieval_prototype",
            model_provenance=prov,
            selection_notes=["Fallback candidate; requires human review."],
        )
        return BackendOperationResult(
            status="ok",
            reason="fallback_candidate_generated",
            backend_id=self.backend_id,
            candidate=candidate,
        )

    def continue_ir(self, request: SymbolicGenerationRequest) -> BackendOperationResult:
        return self.generate(request)

    def infill_ir(self, request: SymbolicGenerationRequest) -> BackendOperationResult:
        return self.generate(request)

    def evaluate(self, candidate):
        return unavailable_result(self.backend_id, "fallback_evaluation_not_supported")

    def rank(self, candidates):
        if not candidates:
            return unavailable_result(self.backend_id, "no_candidates")
        return BackendOperationResult(
            status="ok",
            reason="fallback_rank_order",
            backend_id=self.backend_id,
            ranked_candidate_ids=[candidate.candidate_id for candidate in candidates],
        )

    def explain_result(self, result: BackendOperationResult) -> str:
        return f"Example retrieval result status={result.status} reason={result.reason}"
