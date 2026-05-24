from __future__ import annotations

from .theory_schema import clamp01


def reliability_from_row(row: dict, music_intelligence_row: dict | None = None) -> float:
    if music_intelligence_row:
        score = music_intelligence_row.get("scores", {}).get("transcription_reliability_score")
        if score is not None:
            return clamp01(score)
        direct = music_intelligence_row.get("transcription_confidence")
        if direct is not None:
            return clamp01(direct)
    direct_row = row.get("transcription_confidence")
    if direct_row is not None:
        return clamp01(direct_row)
    hr = row.get("human_rating")
    if isinstance(hr, (int, float)):
        return clamp01(float(hr) / 10.0)
    return 0.35


def confidence_gate_blocked(reliability: float) -> bool:
    return reliability < 0.25
