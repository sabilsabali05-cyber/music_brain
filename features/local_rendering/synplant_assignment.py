from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SynplantAssignment:
    texture_intent: str
    use_synplant: bool
    target_role: str
    fallback_category: str
    reason: str
    is_composer: bool = False


def _fallback_category(track_role: str) -> str:
    role = track_role.lower().strip()
    if role in {"bass", "lead", "pad", "texture"}:
        return role
    if "chord" in role or "harmony" in role:
        return "keys"
    return "instrument"


def assign_synplant_for_intent(
    *,
    texture_intent: str,
    track_role: str,
    synplant_enabled: bool,
    synplant_available: bool,
    bass_role_configured: bool,
) -> SynplantAssignment:
    intent = texture_intent.strip().lower()
    fallback = _fallback_category(track_role)
    if not synplant_enabled:
        return SynplantAssignment(
            texture_intent=intent,
            use_synplant=False,
            target_role="",
            fallback_category=fallback,
            reason="synplant_disabled",
        )
    if not synplant_available:
        return SynplantAssignment(
            texture_intent=intent,
            use_synplant=False,
            target_role="",
            fallback_category=fallback,
            reason="synplant_unavailable",
        )

    mapping = {
        "weird_but_musical": "lead" if "lead" in track_role.lower() else "texture",
        "warm_emotional_chord_bed": "pad",
        "haunted_noise_tail": "texture",
        "fragile_human_breath": "lead" if "lead" in track_role.lower() else "pad",
        "machine_pulse": "synth",
    }

    if intent == "bass_motion_driven":
        if bass_role_configured:
            return SynplantAssignment(
                texture_intent=intent,
                use_synplant=True,
                target_role="bass",
                fallback_category=fallback,
                reason="mapped_bass_motion_driven",
            )
        return SynplantAssignment(
            texture_intent=intent,
            use_synplant=False,
            target_role="",
            fallback_category=fallback,
            reason="bass_synplant_not_configured",
        )

    target = mapping.get(intent, "")
    if not target:
        return SynplantAssignment(
            texture_intent=intent,
            use_synplant=False,
            target_role="",
            fallback_category=fallback,
            reason="intent_not_mapped",
        )
    return SynplantAssignment(
        texture_intent=intent,
        use_synplant=True,
        target_role=target,
        fallback_category=fallback,
        reason=f"mapped_{intent}",
    )
