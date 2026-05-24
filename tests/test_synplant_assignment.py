from __future__ import annotations

from features.local_rendering.synplant_assignment import assign_synplant_for_intent


def test_synplant_assignment_maps_required_intents() -> None:
    assignment = assign_synplant_for_intent(
        texture_intent="weird_but_musical",
        track_role="lead",
        synplant_enabled=True,
        synplant_available=True,
        bass_role_configured=True,
    )
    assert assignment.use_synplant is True
    assert assignment.target_role in {"lead", "texture"}
    assert assignment.is_composer is False

    assignment = assign_synplant_for_intent(
        texture_intent="warm_emotional_chord_bed",
        track_role="chords",
        synplant_enabled=True,
        synplant_available=True,
        bass_role_configured=True,
    )
    assert assignment.use_synplant is True
    assert assignment.target_role == "pad"

    assignment = assign_synplant_for_intent(
        texture_intent="haunted_noise_tail",
        track_role="texture",
        synplant_enabled=True,
        synplant_available=True,
        bass_role_configured=True,
    )
    assert assignment.use_synplant is True
    assert assignment.target_role == "texture"

    assignment = assign_synplant_for_intent(
        texture_intent="fragile_human_breath",
        track_role="lead",
        synplant_enabled=True,
        synplant_available=True,
        bass_role_configured=True,
    )
    assert assignment.use_synplant is True
    assert assignment.target_role in {"lead", "pad"}

    assignment = assign_synplant_for_intent(
        texture_intent="machine_pulse",
        track_role="texture",
        synplant_enabled=True,
        synplant_available=True,
        bass_role_configured=True,
    )
    assert assignment.use_synplant is True
    assert assignment.target_role == "synth"


def test_bass_motion_driven_requires_bass_configuration() -> None:
    disabled = assign_synplant_for_intent(
        texture_intent="bass_motion_driven",
        track_role="bass",
        synplant_enabled=True,
        synplant_available=True,
        bass_role_configured=False,
    )
    assert disabled.use_synplant is False
    assert disabled.reason == "bass_synplant_not_configured"

    enabled = assign_synplant_for_intent(
        texture_intent="bass_motion_driven",
        track_role="bass",
        synplant_enabled=True,
        synplant_available=True,
        bass_role_configured=True,
    )
    assert enabled.use_synplant is True
    assert enabled.target_role == "bass"


def test_missing_synplant_falls_back_safely() -> None:
    assignment = assign_synplant_for_intent(
        texture_intent="weird_but_musical",
        track_role="lead",
        synplant_enabled=True,
        synplant_available=False,
        bass_role_configured=True,
    )
    assert assignment.use_synplant is False
    assert assignment.fallback_category == "lead"
    assert assignment.reason == "synplant_unavailable"
