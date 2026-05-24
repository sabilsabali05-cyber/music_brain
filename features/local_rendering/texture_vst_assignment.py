from __future__ import annotations

from .vst_matcher import match_plugin_for_role
from .vst_registry_schema import VstRegistry


def fallback_category_for_role(track_role: str) -> str:
    role = track_role.lower()
    mapping = {
        "piano": "keys",
        "keys": "keys",
        "pad": "pad",
        "bass": "bass",
        "lead": "lead",
        "texture": "texture",
        "drums": "drum",
        "drum": "drum",
    }
    for key, category in mapping.items():
        if key in role:
            return category
    return "instrument"


def assign_plugin_for_texture(
    registry: VstRegistry,
    track_role: str,
    texture_intent: str,
    preferred_plugin_id: str = "",
) -> tuple[str, str, str]:
    fallback_category = fallback_category_for_role(track_role)
    plugin = match_plugin_for_role(
        registry=registry,
        track_role=track_role,
        texture_intent=texture_intent,
        preferred_plugin_id=preferred_plugin_id,
        preferred_category=fallback_category,
    )
    if plugin is None:
        return "", "", fallback_category
    preset = plugin.preset_names[0] if plugin.preset_names else ""
    return plugin.plugin_id, preset, fallback_category
