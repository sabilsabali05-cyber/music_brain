from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .ratio_schema import RatioObservation, clamp01


@dataclass(frozen=True)
class RatioGenerationMapping:
    domain: str
    ratio_name: str
    confidence: float
    generation_function: str
    generation_implication: str
    control_updates: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", clamp01(self.confidence))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def map_ratio_observation_to_generation_controls(observation: RatioObservation) -> RatioGenerationMapping:
    if observation.status != "observed" or observation.target_ratio is None:
        return RatioGenerationMapping(
            domain=observation.domain,
            ratio_name=observation.ratio_name,
            confidence=observation.confidence * 0.5,
            generation_function="skip_or_soft_hint",
            generation_implication="No hard ratio lock due to missing evidence.",
            control_updates={},
            notes=["observation not confirmed"],
        )

    domain = observation.domain
    ratio = float(observation.target_ratio)
    if domain == "section":
        return RatioGenerationMapping(
            domain=domain,
            ratio_name=observation.ratio_name,
            confidence=observation.confidence,
            generation_function="place_section_pivot",
            generation_implication="Use ratio as section boundary/climax anchor in timeline.",
            control_updates={"section_ratio_target": ratio},
        )
    if domain == "phrase":
        return RatioGenerationMapping(
            domain=domain,
            ratio_name=observation.ratio_name,
            confidence=observation.confidence,
            generation_function="scale_phrase_lengths",
            generation_implication="Apply proportional phrase lengths across adjacent phrases.",
            control_updates={"phrase_ratio_target": ratio},
        )
    if domain == "rhythm":
        return RatioGenerationMapping(
            domain=domain,
            ratio_name=observation.ratio_name,
            confidence=observation.confidence,
            generation_function="weight_subdivision_grid",
            generation_implication="Prioritize pulse subdivisions that approximate observed rhythm ratio.",
            control_updates={"rhythm_ratio_target": ratio},
        )
    if domain == "harmonic":
        return RatioGenerationMapping(
            domain=domain,
            ratio_name=observation.ratio_name,
            confidence=observation.confidence,
            generation_function="shape_harmonic_change_rate",
            generation_implication="Guide harmonic rhythm / interval pacing toward ratio relation.",
            control_updates={"interval_ratio_target": ratio},
        )
    if domain == "motif":
        return RatioGenerationMapping(
            domain=domain,
            ratio_name=observation.ratio_name,
            confidence=observation.confidence,
            generation_function="scale_motif_return_spacing",
            generation_implication="Control motif return cadence and density with ratio spacing.",
            control_updates={"density_ratio_target": ratio},
        )
    return RatioGenerationMapping(
        domain=domain,
        ratio_name=observation.ratio_name,
        confidence=clamp01(observation.confidence * 0.8),
        generation_function="attach_ratio_metadata",
        generation_implication="Expose ratio as soft metadata only.",
        control_updates={},
        notes=["unmapped domain"],
    )

