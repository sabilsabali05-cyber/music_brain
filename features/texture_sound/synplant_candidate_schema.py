from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

GenerationMethod = Literal["manual", "semi_automated", "automated_unknown"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SynplantGenerationSession:
    session_id: str
    seed_sample_id: str
    seed_audio_path: str
    generation_method: GenerationMethod = "manual"
    notes: str = ""
    limitations: list[str] = field(default_factory=list)


@dataclass
class SynplantPatchCandidate:
    session_id: str
    candidate_id: str
    patch_ref: str
    rendered_audio_ref: str | None = None
    selected: bool = False
    limitations: list[str] = field(default_factory=list)


@dataclass
class SynplantPatchSelection:
    session_id: str
    candidate_id: str
    selected: bool
    selection_reason: str = ""


@dataclass
class SynplantRenderResult:
    session_id: str
    candidate_id: str
    rendered_audio_ref: str
    created_at: str = field(default_factory=now_iso)


@dataclass
class SynplantFeedbackRecord:
    session_id: str
    candidate_id: str
    human_rating: float | None = None
    model_rating: float | None = None
    limitations: list[str] = field(default_factory=list)
