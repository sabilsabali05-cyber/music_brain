from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
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
class NamedRatio:
    name: str
    numerator: float
    denominator: float
    decimal_value: float
    description: str
    tolerance: float = 0.08

    def __post_init__(self) -> None:
        numerator = float(self.numerator)
        denominator = float(self.denominator)
        if denominator <= 0:
            raise ValueError("NamedRatio denominator must be > 0.")
        object.__setattr__(self, "numerator", numerator)
        object.__setattr__(self, "denominator", denominator)
        object.__setattr__(self, "decimal_value", float(self.decimal_value))
        object.__setattr__(self, "tolerance", max(0.0001, float(self.tolerance)))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RatioObservation:
    observation_id: str
    source_artifact: str
    source_item_id: str
    domain: str
    ratio_name: str
    observed_numerator: float | None
    observed_denominator: float | None
    observed_ratio: float | None
    target_ratio: float | None
    absolute_error: float | None
    within_tolerance: bool
    confidence: float
    evidence_kind: str
    evidence_excerpt: str
    status: str
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", clamp01(self.confidence))
        status = str(self.status).strip().lower() or "unknown"
        if status not in {"observed", "unavailable", "unknown"}:
            status = "unknown"
        object.__setattr__(self, "status", status)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RatioControlProfile:
    profile_id: str
    selected_ratios: list[str]
    target_duration_seconds: float
    climax_ratio_name: str
    section_ratio_name: str
    phrase_ratio_name: str
    rhythm_ratio_name: str
    interval_ratio_name: str
    density_ratio_name: str
    strictness: float
    confidence: float
    rationale: str
    evidence_observation_ids: list[str] = field(default_factory=list)
    unavailable_domains: list[str] = field(default_factory=list)
    unknown_domains: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "target_duration_seconds", max(1.0, float(self.target_duration_seconds)))
        object.__setattr__(self, "strictness", clamp01(self.strictness))
        object.__setattr__(self, "confidence", clamp01(self.confidence))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def named_ratio_catalog() -> dict[str, NamedRatio]:
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    return {
        "1:1": NamedRatio("1:1", 1.0, 1.0, 1.0, "Unison/identity ratio."),
        "2:1": NamedRatio("2:1", 2.0, 1.0, 2.0, "Octave/simple doubling ratio."),
        "3:2": NamedRatio("3:2", 3.0, 2.0, 1.5, "Perfect-fifth style ratio."),
        "4:3": NamedRatio("4:3", 4.0, 3.0, 4.0 / 3.0, "Perfect-fourth style ratio."),
        "5:4": NamedRatio("5:4", 5.0, 4.0, 1.25, "Major-third style ratio."),
        "6:5": NamedRatio("6:5", 6.0, 5.0, 1.2, "Minor-third style ratio."),
        "5:3": NamedRatio("5:3", 5.0, 3.0, 5.0 / 3.0, "Major-sixth style ratio."),
        "8:5": NamedRatio("8:5", 8.0, 5.0, 1.6, "Minor-sixth style ratio."),
        "5:8": NamedRatio("5:8", 5.0, 8.0, 0.625, "Inverse minor-sixth pacing ratio."),
        "8:13": NamedRatio("8:13", 8.0, 13.0, 8.0 / 13.0, "Fibonacci inverse relation."),
        "golden_ratio_phi": NamedRatio("golden_ratio_phi", phi, 1.0, phi, "Golden ratio (phi)."),
        "golden_section_0_618": NamedRatio(
            "golden_section_0_618", 0.61803398875, 1.0, 0.61803398875, "Golden section proportion."
        ),
        "inverse_phi_0_382": NamedRatio(
            "inverse_phi_0_382", 0.38196601125, 1.0, 0.38196601125, "Inverse golden section proportion."
        ),
    }

