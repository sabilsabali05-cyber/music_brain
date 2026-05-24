from __future__ import annotations

from .theory_schema import VoiceLeadingUnderstanding, clamp01


def analyze_voice_leading(row: dict, transcription_reliability_score: float) -> tuple[VoiceLeadingUnderstanding, dict[str, float]]:
    melody_quality = row.get("melody_quality")
    arrangement_quality = row.get("arrangement_quality")
    mq = clamp01((float(melody_quality) / 10.0) if isinstance(melody_quality, (int, float)) else 0.2)
    aq = clamp01((float(arrangement_quality) / 10.0) if isinstance(arrangement_quality, (int, float)) else 0.2)
    stepwise = clamp01(0.25 + mq * 0.6)
    leap_ratio = clamp01(1.0 - stepwise)
    parallel_risk = clamp01(0.75 - aq * 0.5)
    bass_support = clamp01((aq * 0.6 + mq * 0.4))
    confidence = clamp01((mq + aq + transcription_reliability_score) / 3.0)
    understanding = VoiceLeadingUnderstanding(
        not_applicable=confidence < 0.2,
        stepwise_motion_ratio=stepwise,
        leap_ratio=leap_ratio,
        likely_parallel_risk=parallel_risk,
        bass_support_quality=bass_support,
        confidence=confidence,
        reasons=["derived from melody/arrangement quality proxies"],
    )
    return understanding, {"voice_leading_score": clamp01((stepwise * 0.5 + bass_support * 0.5))}
