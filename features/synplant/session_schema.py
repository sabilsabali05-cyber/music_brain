from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Literal

GenerationMethod = Literal["manual", "assisted", "automated_unknown"]
SeedSourcePolicy = Literal[
    "user_owned_training_candidate",
    "production_only_training_excluded",
    "splice_production_only",
    "unknown_blocked",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_seed_policy(policy: SeedSourcePolicy, *, human_rating: int | None) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if policy in {"production_only_training_excluded", "splice_production_only", "unknown_blocked"}:
        return True, errors
    if policy == "user_owned_training_candidate" and (human_rating is None or human_rating < 1 or human_rating > 5):
        errors.append("human rating required (1-5) before training eligibility")
    return len(errors) == 0, errors


@dataclass
class SynplantSeedCandidate:
    seed_sample_id: str
    track_role: str
    source_policy: SeedSourcePolicy
    public_label: str
    fit_score: float = 0.0
    fit_notes: list[str] = field(default_factory=list)
    local_source_path_private: str = ""
    generation_method: GenerationMethod = "manual"
    limitations: list[str] = field(default_factory=lambda: ["Synplant automation not implemented."])


@dataclass
class SynplantPatchCandidate:
    patch_ref: str
    seed_sample_id: str
    source_policy_inherited: SeedSourcePolicy
    generation_method: GenerationMethod = "manual"
    patch_notes: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=lambda: ["Derived patch inherits seed source restrictions."])


@dataclass
class SynplantPatchSelection:
    session_id: str
    track_role: str
    seed_sample_id: str
    patch_ref: str
    selected: bool
    human_rating: int | None
    selection_reason: str
    source_policy_inherited: SeedSourcePolicy
    training_allowed: bool
    production_use_allowed: bool
    notes: str = ""


@dataclass
class SynplantRenderLog:
    session_id: str
    track_role: str
    patch_ref: str
    rendered_audio_ref: str
    generation_method: GenerationMethod = "manual"
    notes: str = ""
    limitations: list[str] = field(default_factory=lambda: ["Render import only; no automated render pipeline."])


@dataclass
class SynplantSessionFeedback:
    session_id: str
    track_role: str
    patch_ref: str
    human_rating: int
    selected: bool
    training_allowed: bool
    production_use_allowed: bool
    source_policy_inherited: SeedSourcePolicy
    notes: str = ""


@dataclass
class SynplantSessionPlan:
    session_id: str
    ableton_project_folder: str
    generation_method: GenerationMethod = "manual"
    automation_claimed: bool = False
    seed_candidates: list[SynplantSeedCandidate] = field(default_factory=list)
    patch_candidates: list[SynplantPatchCandidate] = field(default_factory=list)
    patch_selections: list[SynplantPatchSelection] = field(default_factory=list)
    render_logs: list[SynplantRenderLog] = field(default_factory=list)
    feedback_rows: list[SynplantSessionFeedback] = field(default_factory=list)
    limitations: list[str] = field(
        default_factory=lambda: [
            "No Synplant automation claim.",
            "Human rating required before any training eligibility.",
            "Derived patch inherits source restrictions from seed.",
        ]
    )
    created_at: str = field(default_factory=now_iso)

    def as_dict(self) -> dict:
        return asdict(self)
