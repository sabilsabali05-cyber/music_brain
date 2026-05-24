from __future__ import annotations

from .theory_schema import FrameworkApplicability, clamp01


FRAMEWORKS: list[str] = [
    "western_functional_harmony",
    "jazz_extended_harmony",
    "gospel_choral_movement",
    "modal_nonfunctional_harmony",
    "neo_riemannian_chromatic_movement",
    "counterpoint_voice_leading",
    "rhythm_groove",
    "hip_hop_loop_form",
    "texture_timbre",
    "microtonal_pitch_bend_awareness",
]


def _yes(framework: str, confidence: float, reason: str) -> FrameworkApplicability:
    return FrameworkApplicability(
        framework=framework,
        applicable=True,
        not_applicable=False,
        confidence=clamp01(confidence),
        reasons=[reason],
    )


def _no(framework: str, confidence: float, reason: str) -> FrameworkApplicability:
    return FrameworkApplicability(
        framework=framework,
        applicable=False,
        not_applicable=True,
        confidence=clamp01(confidence),
        reasons=[reason],
    )


def infer_framework_applicability(
    *,
    harmonic_strength: float,
    chromatic_hint: float,
    rhythmic_strength: float,
    loop_tendency: float,
    texture_strength: float,
    microtonal_evidence: bool,
    choir_hint: bool,
) -> dict[str, FrameworkApplicability]:
    out: dict[str, FrameworkApplicability] = {}
    out["western_functional_harmony"] = (
        _yes("western_functional_harmony", harmonic_strength, "cadential movement hints present")
        if harmonic_strength >= 0.45
        else _no("western_functional_harmony", 1.0 - harmonic_strength, "insufficient tonal evidence")
    )
    out["jazz_extended_harmony"] = (
        _yes("jazz_extended_harmony", (harmonic_strength + chromatic_hint) / 2.0, "color-tone behavior present")
        if harmonic_strength >= 0.35 and chromatic_hint >= 0.3
        else _no("jazz_extended_harmony", 0.7, "no clear extension evidence")
    )
    out["gospel_choral_movement"] = (
        _yes("gospel_choral_movement", 0.7 if choir_hint else 0.55, "choral-style movement hints present")
        if choir_hint
        else _no("gospel_choral_movement", 0.75, "choral evidence absent")
    )
    out["modal_nonfunctional_harmony"] = (
        _yes("modal_nonfunctional_harmony", max(0.4, 1.0 - harmonic_strength), "non-functional center likely")
        if harmonic_strength < 0.55
        else _no("modal_nonfunctional_harmony", 0.55, "functional pull dominates")
    )
    out["neo_riemannian_chromatic_movement"] = (
        _yes("neo_riemannian_chromatic_movement", chromatic_hint, "chromatic planing/motion present")
        if chromatic_hint >= 0.45
        else _no("neo_riemannian_chromatic_movement", 0.8, "chromatic evidence weak")
    )
    out["counterpoint_voice_leading"] = (
        _yes("counterpoint_voice_leading", max(0.4, harmonic_strength), "multi-voice movement analyzable")
        if harmonic_strength >= 0.3
        else _no("counterpoint_voice_leading", 0.65, "insufficient voice evidence")
    )
    out["rhythm_groove"] = (
        _yes("rhythm_groove", rhythmic_strength, "pulse/groove evidence present")
        if rhythmic_strength >= 0.25
        else _no("rhythm_groove", 0.85, "rhythmic evidence sparse")
    )
    out["hip_hop_loop_form"] = (
        _yes("hip_hop_loop_form", loop_tendency, "loop-based structure tendency")
        if loop_tendency >= 0.45
        else _no("hip_hop_loop_form", 0.7, "through-composed tendency stronger")
    )
    out["texture_timbre"] = (
        _yes("texture_timbre", texture_strength, "texture/layer evidence present")
        if texture_strength >= 0.25
        else _no("texture_timbre", 0.8, "texture evidence weak")
    )
    out["microtonal_pitch_bend_awareness"] = (
        _yes("microtonal_pitch_bend_awareness", 0.7, "explicit pitch-bend/microtonal evidence")
        if microtonal_evidence
        else _no("microtonal_pitch_bend_awareness", 0.9, "no microtonal evidence")
    )
    return out
