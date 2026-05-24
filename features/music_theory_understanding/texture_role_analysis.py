from __future__ import annotations

from .theory_schema import TextureRoleUnderstanding, clamp01


def analyze_texture_roles(row: dict, transcription_reliability_score: float) -> tuple[TextureRoleUnderstanding, dict[str, float]]:
    texture = row.get("texture_quality")
    arrangement = row.get("arrangement_quality")
    weirdness = row.get("weirdness_quality")
    t = clamp01((float(texture) / 10.0) if isinstance(texture, (int, float)) else 0.2)
    a = clamp01((float(arrangement) / 10.0) if isinstance(arrangement, (int, float)) else 0.2)
    w = clamp01((float(weirdness) / 10.0) if isinstance(weirdness, (int, float)) else 0.2)
    density = clamp01(t * 0.8 + w * 0.1)
    separation = clamp01(t * 0.7 + a * 0.2)
    atmosphere = clamp01(w * 0.6 + t * 0.2)
    lead = clamp01(a * 0.5 + t * 0.2)
    understanding = TextureRoleUnderstanding(
        not_applicable=(t < 0.1 and transcription_reliability_score < 0.25),
        density_level=density,
        layer_separation=separation,
        atmosphere_weight=atmosphere,
        lead_presence=lead,
        confidence=clamp01((t + transcription_reliability_score) / 2.0),
        reasons=["texture role from texture/arrangement proxy fields"],
    )
    return understanding, {"texture_value_score": clamp01((density + separation + atmosphere) / 3.0)}
