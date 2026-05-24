from __future__ import annotations

from features.ratio_understanding.ratio_schema import RatioControlProfile, RatioObservation, named_ratio_catalog


def test_named_ratio_catalog_contains_required_ratio_names() -> None:
    catalog = named_ratio_catalog()
    required = {
        "1:1",
        "2:1",
        "3:2",
        "4:3",
        "5:4",
        "6:5",
        "5:3",
        "8:5",
        "5:8",
        "8:13",
        "golden_ratio_phi",
        "golden_section_0_618",
        "inverse_phi_0_382",
    }
    assert required.issubset(catalog.keys())


def test_ratio_observation_clamps_confidence_and_status() -> None:
    obs = RatioObservation(
        observation_id="o1",
        source_artifact="demo.mid",
        source_item_id="demo",
        domain="section",
        ratio_name="3:2",
        observed_numerator=3.0,
        observed_denominator=2.0,
        observed_ratio=1.5,
        target_ratio=1.5,
        absolute_error=0.0,
        within_tolerance=True,
        confidence=1.8,
        evidence_kind="symbolic",
        evidence_excerpt="x",
        status="INVALID",
    )
    assert obs.confidence == 1.0
    assert obs.status == "unknown"


def test_ratio_control_profile_normalizes_fields() -> None:
    profile = RatioControlProfile(
        profile_id="p1",
        selected_ratios=["3:2"],
        target_duration_seconds=0.1,
        climax_ratio_name="golden_section_0_618",
        section_ratio_name="golden_section_0_618",
        phrase_ratio_name="3:2",
        rhythm_ratio_name="5:3",
        interval_ratio_name="5:4",
        density_ratio_name="8:5",
        strictness=2.0,
        confidence=-0.1,
        rationale="demo",
    )
    assert profile.target_duration_seconds >= 1.0
    assert profile.strictness == 1.0
    assert profile.confidence == 0.0

