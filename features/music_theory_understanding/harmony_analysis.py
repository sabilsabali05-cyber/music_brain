from __future__ import annotations

from .theory_frameworks import infer_framework_applicability
from .theory_schema import HarmonyUnderstanding, clamp01


def analyze_harmony(row: dict, transcription_reliability_score: float) -> tuple[HarmonyUnderstanding, dict[str, float]]:
    harmony_quality = row.get("harmony_quality")
    weirdness_quality = row.get("weirdness_quality")
    tags = {str(tag).lower() for tag in row.get("tags", []) if isinstance(tag, str)}
    harmonic_interest = clamp01((float(harmony_quality) / 10.0) if isinstance(harmony_quality, (int, float)) else 0.15)
    chromatic_hint = clamp01((float(weirdness_quality) / 10.0) if isinstance(weirdness_quality, (int, float)) else 0.1)
    random_clash_risk = harmonic_interest < 0.2 and chromatic_hint > 0.5
    valuable_weirdness = chromatic_hint >= 0.5 and not random_clash_risk
    movement = "stable_loop" if harmonic_interest < 0.35 else "functional_or_directed"
    if chromatic_hint > 0.65:
        movement = "chromatic_color_motion"
    center_hint = None if harmonic_interest < 0.2 else "ambiguous_center"
    if harmonic_interest > 0.5:
        center_hint = "likely_tonal_center"

    frameworks = infer_framework_applicability(
        harmonic_strength=harmonic_interest,
        chromatic_hint=chromatic_hint,
        rhythmic_strength=0.4,
        loop_tendency=0.5,
        texture_strength=0.4,
        microtonal_evidence=("microtonal" in tags or "pitch-bend" in tags),
        choir_hint=("choir" in tags or "gospel" in tags),
    )
    confidence = clamp01((harmonic_interest * 0.7 + transcription_reliability_score * 0.3))
    understanding = HarmonyUnderstanding(
        not_applicable=harmonic_interest <= 0.15 and transcription_reliability_score < 0.3,
        center_hint=center_hint,
        movement_description=movement,
        color_tones=["b9/#11-style tension"] if chromatic_hint > 0.55 else [],
        valuable_weirdness=valuable_weirdness,
        random_clash_risk=random_clash_risk,
        confidence=confidence,
        applicability_by_framework=list(frameworks.values()),
        reasons=[
            "confidence adjusted by transcription reliability",
            "not_applicable used when harmonic evidence is too weak",
        ],
    )
    return understanding, {"harmonic_interest_score": harmonic_interest, "chord_movement_score": clamp01((harmonic_interest * 0.8 + (1.0 - random_clash_risk) * 0.2))}
