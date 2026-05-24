from __future__ import annotations

from .theory_schema import RhythmGrooveUnderstanding, clamp01


def analyze_rhythm(row: dict, transcription_reliability_score: float) -> tuple[RhythmGrooveUnderstanding, dict[str, float]]:
    rhythm_quality = row.get("rhythm_quality")
    weirdness = row.get("weirdness_quality")
    r = clamp01((float(rhythm_quality) / 10.0) if isinstance(rhythm_quality, (int, float)) else 0.2)
    w = clamp01((float(weirdness) / 10.0) if isinstance(weirdness, (int, float)) else 0.2)
    pulse = clamp01(r * 0.8 + transcription_reliability_score * 0.2)
    sync = clamp01(w * 0.6 + r * 0.2)
    groove = clamp01((pulse + r) / 2.0)
    loop_friendliness = clamp01((groove + (1.0 - sync * 0.4)) / 2.0)
    understanding = RhythmGrooveUnderstanding(
        not_applicable=(r < 0.12 and transcription_reliability_score < 0.25),
        pulse_clarity=pulse,
        syncopation_hint=sync,
        groove_pocket_value=groove,
        loop_friendliness=loop_friendliness,
        confidence=clamp01((r + transcription_reliability_score) / 2.0),
        reasons=["rhythm identity from rhythm_quality and reliability"],
    )
    return understanding, {"rhythm_identity_score": pulse, "groove_value_score": groove}
