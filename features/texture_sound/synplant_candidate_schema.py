from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

GenerationMethod = Literal["manual", "semi_automated", "automated_unknown"]
TrackRole = Literal[
    "bass",
    "lead",
    "pad",
    "pluck",
    "percussion",
    "fx",
    "riser",
    "choir_like",
    "texture_bed",
    "drone",
    "counter_melody",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SynplantGenerationSession:
    session_id: str
    composition_id: str
    track_role: TrackRole
    requested_texture_description: str
    seed_sample_id: str
    seed_audio_path: str
    generation_method: GenerationMethod = "manual"
    session_operator: str = "human"
    synplant_version: str = ""
    limitations: list[str] = field(default_factory=list)
    started_at: str = field(default_factory=now_iso)
    ended_at: str | None = None


@dataclass
class SynplantPatchCandidate:
    session_id: str
    candidate_id: str
    track_role: TrackRole
    seed_sample_id: str
    seed_audio_path: str
    synplant_patch_ref: str
    rendered_audio_ref: str | None = None
    candidate_rank: int = 0
    selected: bool = False
    human_rating: float | None = None
    model_rating: float | None = None
    fit_to_role_score: float | None = None
    fit_to_mix_score: float | None = None
    novelty_score: float | None = None
    reuse_allowed: bool = False
    limitations: list[str] = field(default_factory=list)


@dataclass
class SynplantPatchSelection:
    session_id: str
    composition_id: str
    track_role: TrackRole
    selected_candidate_id: str
    selected: bool = True
    selection_reason: str = ""
    selected_by: Literal["human", "model", "hybrid"] = "human"
    selected_at: str = field(default_factory=now_iso)


@dataclass
class SynplantRenderResult:
    session_id: str
    candidate_id: str
    composition_id: str
    track_role: TrackRole
    synplant_patch_ref: str
    rendered_audio_ref: str
    render_format: str = "wav"
    reuse_allowed: bool = False
    limitations: list[str] = field(default_factory=list)
    rendered_at: str = field(default_factory=now_iso)


@dataclass
class SynplantFeedbackRecord:
    session_id: str
    candidate_id: str
    composition_id: str
    track_role: TrackRole
    selected: bool
    selection_reason: str
    human_rating: float | None = None
    model_rating: float | None = None
    fit_to_role_score: float | None = None
    fit_to_mix_score: float | None = None
    novelty_score: float | None = None
    feedback_notes: str = ""
    limitations: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)
