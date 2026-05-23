from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

RatioFamily = Literal[
    "simple_integer",
    "just_intonation",
    "polyrhythm",
    "fibonacci",
    "golden_ratio",
    "silver_ratio",
    "plastic_number",
    "root_ratio",
    "exponential",
    "logarithmic",
    "custom",
]


@dataclass
class RatioDefinition:
    ratio_name: str
    ratio_family: RatioFamily
    numerator: float
    denominator: float
    decimal_value: float
    tolerance: float = 0.0


@dataclass
class RatioCompositionConstraint:
    constraint_id: str
    ratio: RatioDefinition
    target_role: str
    notes: str = ""


@dataclass
class RatioStructurePlan:
    plan_id: str
    constraints: list[RatioCompositionConstraint] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
