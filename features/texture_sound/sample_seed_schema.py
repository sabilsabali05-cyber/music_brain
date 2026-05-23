from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

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
AuthorizationStatus = Literal["authorized", "restricted", "unknown", "pending_review"]
ReviewStatus = Literal["approved", "review_required", "rejected", "unknown"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SampleSeedFeatureProfile:
    pitch_profile: dict[str, Any] = field(default_factory=dict)
    spectral_profile: dict[str, Any] = field(default_factory=dict)
    transient_profile: dict[str, Any] = field(default_factory=dict)
    noise_profile: dict[str, Any] = field(default_factory=dict)
    harmonicity_profile: dict[str, Any] = field(default_factory=dict)


@dataclass
class SampleRoleCandidate:
    role: TrackRole
    confidence: float = 0.0
    rationale: str = ""
    evidence_refs: list[str] = field(default_factory=list)


@dataclass
class SampleSeedRecord:
    sample_id: str
    source_path: str
    duration_seconds: float
    file_hash: str
    feature_profile: SampleSeedFeatureProfile
    texture_tags: list[str] = field(default_factory=list)
    role_candidates: list[SampleRoleCandidate] = field(default_factory=list)
    authorization_status: AuthorizationStatus = "unknown"
    review_status: ReviewStatus = "unknown"
    embedding_refs: list[str] = field(default_factory=list)
    analysis_refs: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)


@dataclass
class SampleSearchQuery:
    query_id: str
    composition_id: str
    track_role: TrackRole
    desired_texture_description: str
    required_tags: list[str] = field(default_factory=list)
    excluded_tags: list[str] = field(default_factory=list)
    max_results: int = 10
    authorization_filter: list[AuthorizationStatus] = field(default_factory=lambda: ["authorized", "unknown"])


@dataclass
class SynplantSeedCandidate:
    sample_id: str
    source_path: str
    track_role: TrackRole
    role_confidence: float
    seed_score: float
    fit_reason: str = ""
    warnings: list[str] = field(default_factory=list)
    feature_snapshot: SampleSeedFeatureProfile = field(default_factory=SampleSeedFeatureProfile)
    embedding_refs: list[str] = field(default_factory=list)
    analysis_refs: list[str] = field(default_factory=list)


@dataclass
class SampleSearchResult:
    query_id: str
    composition_id: str
    track_role: TrackRole
    candidates: list[SynplantSeedCandidate] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=now_iso)
