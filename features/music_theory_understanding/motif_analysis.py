from __future__ import annotations

from .theory_schema import MotifUnderstanding, clamp01


def analyze_motif(row: dict, transcription_reliability_score: float) -> tuple[MotifUnderstanding, dict[str, float]]:
    musicality = row.get("musicality_quality")
    weirdness = row.get("weirdness_quality")
    m = clamp01((float(musicality) / 10.0) if isinstance(musicality, (int, float)) else 0.25)
    w = clamp01((float(weirdness) / 10.0) if isinstance(weirdness, (int, float)) else 0.2)
    recurrence = clamp01(m * 0.75 + 0.1)
    transformability = clamp01(recurrence * 0.7 + w * 0.3)
    understanding = MotifUnderstanding(
        not_applicable=(m < 0.15 and transcription_reliability_score < 0.25),
        motif_cell_detected=recurrence >= 0.33,
        recurrence_density=recurrence,
        transformability=transformability,
        confidence=clamp01((m + transcription_reliability_score) / 2.0),
        reasons=["motif estimate from musicality recurrence proxies"],
    )
    return understanding, {"motif_reusability_score": clamp01((recurrence * 0.55 + transformability * 0.45))}
