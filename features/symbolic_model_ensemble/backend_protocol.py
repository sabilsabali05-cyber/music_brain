from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from features.symbolic_ir import (
    SymbolicBackendCapability,
    SymbolicEvaluationScore,
    SymbolicGenerationCandidate,
    SymbolicGenerationRequest,
    SymbolicModelProvenance,
    SymbolicMusicIR,
    SymbolicNoteEvent,
    SymbolicSection,
    SymbolicTrack,
)

ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT_DIR / "config" / "symbolic_backends"
LOCAL_CONFIG = CONFIG_DIR / "symbolic_backends.local.json"
EXAMPLE_CONFIG = CONFIG_DIR / "symbolic_backends.example.json"


@dataclass
class BackendOperationResult:
    status: str
    reason: str
    backend_id: str
    candidate: SymbolicGenerationCandidate | None = None
    evaluation: SymbolicEvaluationScore | None = None
    ranked_candidate_ids: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


class SymbolicBackendProtocol(Protocol):
    backend_id: str

    def check_available(self) -> SymbolicBackendCapability: ...

    def describe_capabilities(self) -> SymbolicBackendCapability: ...

    def generate(self, request: SymbolicGenerationRequest) -> BackendOperationResult: ...

    def continue_ir(self, request: SymbolicGenerationRequest) -> BackendOperationResult: ...

    def infill_ir(self, request: SymbolicGenerationRequest) -> BackendOperationResult: ...

    def evaluate(self, candidate: SymbolicGenerationCandidate) -> BackendOperationResult: ...

    def rank(self, candidates: list[SymbolicGenerationCandidate]) -> BackendOperationResult: ...

    def explain_result(self, result: BackendOperationResult) -> str: ...


def load_symbolic_backends_config() -> tuple[dict[str, Any], str]:
    if LOCAL_CONFIG.exists():
        source = LOCAL_CONFIG
    elif EXAMPLE_CONFIG.exists():
        source = EXAMPLE_CONFIG
    else:
        return {}, "missing_config"
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}, f"invalid_json:{source.as_posix()}"
    if not isinstance(payload, dict):
        return {}, f"invalid_shape:{source.as_posix()}"
    return payload, source.as_posix()


def backend_settings(backend_id: str) -> tuple[dict[str, Any], str]:
    payload, source = load_symbolic_backends_config()
    if not payload:
        return {}, source
    settings = payload.get(backend_id)
    if not isinstance(settings, dict):
        return {}, f"missing_section:{backend_id}:{source}"
    return settings, source


def unavailable_capability(
    backend_id: str,
    backend_role: str,
    operations: list[str],
    reason: str,
    limitations: list[str] | None = None,
) -> SymbolicBackendCapability:
    return SymbolicBackendCapability(
        backend_id=backend_id,
        backend_role=backend_role,
        supported_operations=operations,
        status="unavailable",
        reason=reason,
        limitations=limitations or [],
    )


def available_capability(
    backend_id: str,
    backend_role: str,
    operations: list[str],
    reason: str = "smoke_test_passed",
    limitations: list[str] | None = None,
) -> SymbolicBackendCapability:
    return SymbolicBackendCapability(
        backend_id=backend_id,
        backend_role=backend_role,
        supported_operations=operations,
        status="available",
        reason=reason,
        limitations=limitations or [],
    )


def unavailable_result(backend_id: str, reason: str) -> BackendOperationResult:
    return BackendOperationResult(status="unavailable", reason=reason, backend_id=backend_id)


def build_placeholder_candidate(
    backend_id: str,
    request: SymbolicGenerationRequest,
    *,
    method: str,
    note_pitch: int = 60,
) -> SymbolicGenerationCandidate:
    ticks_per_bar = 1920
    notes = [
        SymbolicNoteEvent(start_tick=0, duration_tick=480, pitch=note_pitch, velocity=84, channel=0),
        SymbolicNoteEvent(start_tick=480, duration_tick=480, pitch=note_pitch + 2, velocity=80, channel=0),
        SymbolicNoteEvent(start_tick=960, duration_tick=480, pitch=note_pitch + 5, velocity=76, channel=0),
    ]
    ir = SymbolicMusicIR(
        composition_id=f"{request.request_id}_{backend_id}",
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
                end_tick=ticks_per_bar,
                section_goal="placeholder_symbolic_stub",
            )
        ],
        tracks=[
            SymbolicTrack(
                track_id="track_1",
                track_role=request.prompt_spec.requested_track_roles[0] if request.prompt_spec.requested_track_roles else "lead",
                instrument_hint="placeholder_piano",
                note_events=notes,
            )
        ],
        source_backend=backend_id,
        generation_method=method,
        transformation_notes=["placeholder symbolic hook output; replace with real backend inference hook."],
        limitations=["Placeholder conversion hook only; not real model inference output."],
    )
    prov = SymbolicModelProvenance(source_backend=backend_id, generation_method=method)
    if backend_id == "moonbeam":
        prov.provenance_flags["generated_by_moonbeam"] = True
    if backend_id == "midigpt":
        prov.provenance_flags["generated_by_midigpt"] = True
    if backend_id == "text2midi":
        prov.provenance_flags["generated_by_text2midi"] = True
    return SymbolicGenerationCandidate(
        candidate_id=f"{backend_id}_{uuid.uuid4().hex[:10]}",
        ir=ir,
        source_backend=backend_id,
        generation_method=method,
        model_provenance=prov,
        selection_notes=["Needs human review before production or training usage."],
    )
