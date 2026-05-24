from __future__ import annotations

from .theory_schema import FormUnderstanding, clamp01


def analyze_form(row: dict, transcription_reliability_score: float) -> tuple[FormUnderstanding, dict[str, float]]:
    arrangement = row.get("arrangement_quality")
    rhythm_quality = row.get("rhythm_quality")
    a = clamp01((float(arrangement) / 10.0) if isinstance(arrangement, (int, float)) else 0.2)
    r = clamp01((float(rhythm_quality) / 10.0) if isinstance(rhythm_quality, (int, float)) else 0.2)
    through = clamp01(a * 0.7)
    loop = clamp01(r * 0.7 + (1.0 - a) * 0.2)
    sections = 2 + int(round(a * 4))
    dev = clamp01((through + a) / 2.0)
    understanding = FormUnderstanding(
        not_applicable=(a < 0.1 and transcription_reliability_score < 0.25),
        section_count_hint=sections,
        through_composed_tendency=through,
        loop_tendency=loop,
        development_strength=dev,
        confidence=clamp01((a + transcription_reliability_score) / 2.0),
        reasons=["form score inferred from arrangement + rhythm qualities"],
    )
    return understanding, {"form_development_score": dev}
