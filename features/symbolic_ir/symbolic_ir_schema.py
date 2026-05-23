from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


BackendStatus = Literal["available", "unavailable"]


@dataclass
class SymbolicNoteEvent:
    start_tick: int
    duration_tick: int
    pitch: int
    velocity: int
    channel: int


@dataclass
class SymbolicTrack:
    track_id: str
    track_role: str
    instrument_hint: str
    note_events: list[SymbolicNoteEvent] = field(default_factory=list)


@dataclass
class SymbolicSection:
    section_label: str
    start_tick: int
    end_tick: int
    section_goal: str = ""


@dataclass
class SymbolicPromptSpec:
    prompt_text: str
    duration_seconds: float
    tempo: float
    meter: str
    key_hint: str
    ratio_plan: str
    section_labels: list[str] = field(default_factory=list)
    requested_track_roles: list[str] = field(default_factory=list)
    prompt_constraints: dict[str, Any] = field(default_factory=dict)


@dataclass
class SymbolicModelProvenance:
    source_backend: str
    generation_method: str
    transformation_notes: list[str] = field(default_factory=list)
    provenance_flags: dict[str, bool] = field(
        default_factory=lambda: {
            "generated_by_moonbeam": False,
            "generated_by_midigpt": False,
            "generated_by_text2midi": False,
            "evaluated_by_musicbert": False,
            "example_retrieval_fallback": False,
            "not_model_trained_on_user_data": True,
            "needs_human_review": True,
        }
    )
    limitations: list[str] = field(default_factory=list)


@dataclass
class SymbolicMusicIR:
    composition_id: str
    prompt_text: str
    duration_seconds: float
    tempo: float
    meter: str
    key_hint: str
    ratio_plan: str
    section_labels: list[str] = field(default_factory=list)
    sections: list[SymbolicSection] = field(default_factory=list)
    tracks: list[SymbolicTrack] = field(default_factory=list)
    source_backend: str = ""
    generation_method: str = ""
    transformation_notes: list[str] = field(default_factory=list)
    provenance_flags: dict[str, bool] = field(
        default_factory=lambda: {
            "generated_by_moonbeam": False,
            "generated_by_midigpt": False,
            "generated_by_text2midi": False,
            "evaluated_by_musicbert": False,
            "example_retrieval_fallback": False,
            "not_model_trained_on_user_data": True,
            "needs_human_review": True,
        }
    )
    limitations: list[str] = field(default_factory=list)


@dataclass
class SymbolicGenerationRequest:
    request_id: str
    prompt_spec: SymbolicPromptSpec
    task_type: str
    source_backend: str
    seed_ir: SymbolicMusicIR | None = None
    conditioning: dict[str, Any] = field(default_factory=dict)


@dataclass
class SymbolicGenerationCandidate:
    candidate_id: str
    ir: SymbolicMusicIR
    source_backend: str
    generation_method: str
    model_provenance: SymbolicModelProvenance
    selection_notes: list[str] = field(default_factory=list)


@dataclass
class SymbolicEvaluationScore:
    candidate_id: str
    evaluated_by: str
    score: float
    metrics: dict[str, float] = field(default_factory=dict)
    rationale: str = ""


@dataclass
class SymbolicBackendCapability:
    backend_id: str
    backend_role: str
    supported_operations: list[str] = field(default_factory=list)
    status: BackendStatus = "unavailable"
    reason: str = "not_checked"
    limitations: list[str] = field(default_factory=list)
