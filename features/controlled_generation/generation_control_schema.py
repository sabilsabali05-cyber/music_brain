from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


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
class RatioControl:
    ratio_name: str
    target_ratio: float
    measured_ratio: float | None
    tolerance: float
    confidence: float
    strict: bool
    source_observation_ids: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "target_ratio", float(self.target_ratio))
        object.__setattr__(self, "tolerance", max(0.0001, float(self.tolerance)))
        object.__setattr__(self, "confidence", clamp01(self.confidence))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GenerationControlSpec:
    spec_id: str
    generation_id: str
    duration_seconds: float
    bpm: int
    ratio_controls: list[RatioControl]
    preserve_battle_appeal_priority: bool
    flexibility_priority: float
    ratio_musicality_weight: float
    evidence_based_only: bool
    no_cloud_calls: bool
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "duration_seconds", max(1.0, float(self.duration_seconds)))
        object.__setattr__(self, "bpm", max(30, int(self.bpm)))
        object.__setattr__(self, "flexibility_priority", clamp01(self.flexibility_priority))
        object.__setattr__(self, "ratio_musicality_weight", clamp01(self.ratio_musicality_weight))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

