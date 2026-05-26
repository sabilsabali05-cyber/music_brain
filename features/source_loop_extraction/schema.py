from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ExtractedSourceLoop:
    clip_id: str
    source_id: str
    path_hash: str
    source_redacted_path: str
    local_clip_relpath: str
    local_audio_clip_exists: bool
    bars_target: int | None
    start_seconds: float
    duration_seconds: float
    timing_basis: str
    tempo_bpm_estimate: float | None
    tempo_confidence: float
    key_estimate: str | None
    key_confidence: float
    loopability_score: float
    rhythm_density_score: float
    harmonic_region_hint: str
    texture_role_hint: str
    energy_role_hint: str
    analysis_allowed: bool
    retrieval_allowed: bool
    training_allowed: bool
    authorized_for_buddy_generation: bool
    witnesses_available: list[str] = field(default_factory=list)
    witnesses_unavailable: list[str] = field(default_factory=list)
    extraction_notes: list[str] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
