from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .model_witness_schema import redact_private_path


def clamp01(value: float | int | None) -> float:
    if value is None:
        return 0.0
    out = float(value)
    if out < 0.0:
        return 0.0
    if out > 1.0:
        return 1.0
    return out


@dataclass(frozen=True)
class ModelWitnessObservation:
    observation_id: str
    item_id: str
    witness_id: str
    witness_type: str
    backend_status: str
    analysis_allowed: bool
    used_real_backend: bool
    heuristic_witness_label: str
    evidence_summary: str
    evidence_points: list[str]
    confidence: float
    disagreement_tags: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    redacted_source_ref: str = "<PRIVATE_LOCAL_PATH>/unknown"
    raw_payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", clamp01(self.confidence))
        object.__setattr__(self, "redacted_source_ref", redact_private_path(self.redacted_source_ref))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ModelWitnessConsensus:
    consensus_id: str
    item_id: str
    consensus_summary: str
    confidence: float
    witness_count: int
    agreeing_witnesses: list[str]
    disagreements: list[dict[str, Any]]
    qualitative_conflicts: list[str]
    weak_evidence_areas: list[str]
    generative_principles: list[str]
    rejected_principles: list[str]
    blockers: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", clamp01(self.confidence))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
