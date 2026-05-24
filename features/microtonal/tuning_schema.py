from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

TuningKind = Literal["edo", "just_intonation", "custom", "placeholder"]


@dataclass(frozen=True)
class TuningPreset:
    preset_id: str
    kind: TuningKind
    description: str
    intervals_cents: list[float]
    steps_per_octave: int
    placeholder_safe: bool = False
    advisory: str = ""


@dataclass(frozen=True)
class MicrotonalCompositionPlan:
    selected_preset: str
    supported_presets: list[str]
    supported_export_strategies: list[str]
    constraints: dict[str, bool] = field(default_factory=dict)
