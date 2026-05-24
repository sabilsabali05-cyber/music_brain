from __future__ import annotations

from features.ratio_understanding.ratio_schema import RatioObservation
from features.ratio_understanding.ratio_to_generation import map_ratio_observation_to_generation_controls


def test_maps_observed_phrase_ratio_to_generation_control() -> None:
    observation = RatioObservation(
        observation_id="obs1",
        source_artifact="x.mid",
        source_item_id="x",
        domain="phrase",
        ratio_name="3:2",
        observed_numerator=3.0,
        observed_denominator=2.0,
        observed_ratio=1.5,
        target_ratio=1.5,
        absolute_error=0.01,
        within_tolerance=True,
        confidence=0.82,
        evidence_kind="symbolic",
        evidence_excerpt="phrase",
        status="observed",
    )
    mapped = map_ratio_observation_to_generation_controls(observation)
    assert mapped.generation_function == "scale_phrase_lengths"
    assert mapped.control_updates["phrase_ratio_target"] == 1.5


def test_unavailable_observation_becomes_soft_hint() -> None:
    observation = RatioObservation(
        observation_id="obs2",
        source_artifact="x.mid",
        source_item_id="x",
        domain="section",
        ratio_name="unknown",
        observed_numerator=None,
        observed_denominator=None,
        observed_ratio=None,
        target_ratio=None,
        absolute_error=None,
        within_tolerance=False,
        confidence=0.4,
        evidence_kind="symbolic",
        evidence_excerpt="none",
        status="unavailable",
    )
    mapped = map_ratio_observation_to_generation_controls(observation)
    assert mapped.generation_function == "skip_or_soft_hint"
    assert mapped.control_updates == {}

