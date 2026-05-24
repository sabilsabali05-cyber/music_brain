from __future__ import annotations

from .vst_registry_schema import VstPluginEntry, VstRegistry


def match_plugin_for_role(
    registry: VstRegistry,
    track_role: str,
    texture_intent: str = "",
    preferred_plugin_id: str = "",
    preferred_category: str = "",
) -> VstPluginEntry | None:
    if preferred_plugin_id:
        preferred = registry.get_plugin(preferred_plugin_id)
        if preferred and preferred.available:
            return preferred

    lowered_role = track_role.lower()
    lowered_texture = texture_intent.lower()
    lowered_category = preferred_category.lower()

    scored: list[tuple[int, VstPluginEntry]] = []
    for plugin in registry.available_plugins():
        score = 0
        if lowered_role and lowered_role in [item.lower() for item in plugin.roles]:
            score += 6
        if lowered_category and plugin.category.lower() == lowered_category:
            score += 5
        if lowered_texture:
            texture_hits = [item for item in plugin.texture_tags if item.lower() in lowered_texture]
            score += len(texture_hits) * 2
        if plugin.verified_loadable:
            score += 1
        scored.append((score, plugin))

    scored.sort(key=lambda pair: (-pair[0], pair[1].display_name.lower()))
    if not scored:
        return None
    top_score, plugin = scored[0]
    if top_score <= 0:
        return None
    return plugin


def match_midi_fx_plugin(
    registry: VstRegistry,
    fx_role: str,
    preferred_plugin_id: str = "",
) -> VstPluginEntry | None:
    if preferred_plugin_id:
        preferred = registry.get_plugin(preferred_plugin_id)
        if preferred and preferred.available and preferred.category == "midi_fx":
            return preferred

    lowered_role = fx_role.lower().strip()
    scored: list[tuple[int, VstPluginEntry]] = []
    for plugin in registry.available_plugins():
        if plugin.category != "midi_fx":
            continue
        score = 0
        if lowered_role and lowered_role in [item.lower() for item in plugin.roles]:
            score += 8
        if plugin.verified_loadable:
            score += 1
        scored.append((score, plugin))

    scored.sort(key=lambda pair: (-pair[0], pair[1].display_name.lower()))
    if not scored:
        return None
    top_score, plugin = scored[0]
    if top_score <= 0 and lowered_role:
        return None
    return plugin
