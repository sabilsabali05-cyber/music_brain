from __future__ import annotations

from typing import Any

FILE_CONTENT_STATES = {
    "performance_recording",
    "full_song",
    "rap_song",
    "drum_loop",
    "melodic_loop",
    "chord_loop",
    "one_shot_drum",
    "one_shot_synth",
    "vocal_sample",
    "ambient_texture",
    "speech_heavy",
    "unknown",
}

REGION_CONTENT_STATES = {
    "percussive_only",
    "rhythm_dominant",
    "harmonic_dominant",
    "melodic_lead",
    "vocal_dominant",
    "rap_vocal_dominant",
    "polyphonic_full_mix",
    "ambient_low_information",
    "speech_like",
    "transition_build",
    "silence_or_noise",
    "unknown",
}

ANALYSIS_FAMILIES = {
    "rhythm",
    "transient",
    "tempo_grid",
    "swing_groove",
    "harmony",
    "chord_movement",
    "melody",
    "vocal_flow",
    "timbre",
    "texture",
    "semantic",
    "transcription",
    "stitching",
    "training_export",
}

_REGION_ROUTING: dict[str, tuple[set[str], set[str], list[str]]] = {
    "percussive_only": (
        {"rhythm", "transient", "tempo_grid", "swing_groove", "semantic", "training_export"},
        {"harmony", "chord_movement", "melody"},
        ["suppress_hard_chord_labels", "allow_rhythm_motif_labels"],
    ),
    "rhythm_dominant": (
        {"rhythm", "transient", "tempo_grid", "swing_groove", "semantic", "training_export"},
        {"harmony"},
        ["downgrade_chord_labels_without_harmonic_evidence", "prefer_rhythm_labels"],
    ),
    "harmonic_dominant": (
        {"harmony", "chord_movement", "melody", "rhythm", "semantic", "training_export"},
        {"transient"},
        ["allow_chord_labels_if_confident", "allow_rhythm_if_onset_evidence_present"],
    ),
    "melodic_lead": (
        {"melody", "harmony", "rhythm", "semantic", "training_export"},
        {"transient"},
        ["prefer_melodic_phrase_labels", "downgrade_transient_only_labels"],
    ),
    "vocal_dominant": (
        {"vocal_flow", "rhythm", "semantic", "timbre", "training_export"},
        {"chord_movement"},
        ["mark_harmony_labels_weak_without_accompaniment_evidence"],
    ),
    "rap_vocal_dominant": (
        {"vocal_flow", "rhythm", "tempo_grid", "semantic", "training_export"},
        {"chord_movement", "melody"},
        ["prefer_flow_and_phrase_labels", "downgrade_chord_labels_without_support"],
    ),
    "polyphonic_full_mix": (
        ANALYSIS_FAMILIES - {"stitching", "transcription"},
        set(),
        ["require_confidence_and_evidence_for_semantic_labels"],
    ),
    "ambient_low_information": (
        {"texture", "timbre", "semantic", "training_export"},
        {"harmony", "chord_movement", "tempo_grid", "swing_groove"},
        ["suppress_strong_music_theory_labels", "allow_texture_observations"],
    ),
    "speech_like": (
        {"vocal_flow", "semantic", "timbre", "training_export"},
        {"harmony", "chord_movement", "melody"},
        ["suppress_music_theory_labels", "mark_review_required"],
    ),
    "transition_build": (
        {"rhythm", "transient", "texture", "semantic", "training_export"},
        {"chord_movement"},
        ["prefer_transition_descriptors", "downgrade_key_labels_if_unstable"],
    ),
    "silence_or_noise": (
        {"texture", "semantic", "training_export"},
        ANALYSIS_FAMILIES - {"texture", "semantic", "training_export"},
        ["suppress_hard_rhythm_and_harmony_labels", "mark_low_information"],
    ),
    "unknown": (
        {"semantic", "training_export"},
        {"chord_movement"},
        ["mark_review_required_when_label_is_semantic"],
    ),
}


def route_for_content_state(content_state: str) -> tuple[list[str], list[str], list[str]]:
    recommended, suppressed, gating_rules = _REGION_ROUTING.get(
        content_state,
        _REGION_ROUTING["unknown"],
    )
    return sorted(recommended), sorted(suppressed), gating_rules


def make_route_decision(
    *,
    content_state: str,
    confidence: float,
    evidence: dict[str, Any],
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    recommended, suppressed, gating_rules = route_for_content_state(content_state)
    return {
        "content_state": content_state if content_state in REGION_CONTENT_STATES.union(FILE_CONTENT_STATES) else "unknown",
        "confidence": max(0.0, min(1.0, float(confidence))),
        "evidence": evidence,
        "recommended_analysis_families": recommended,
        "suppressed_analysis_families": suppressed,
        "label_gating_rules": gating_rules,
        "limitations": list(limitations or []),
    }
