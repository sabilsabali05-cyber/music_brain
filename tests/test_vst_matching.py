from __future__ import annotations

from features.local_rendering.vst_matcher import match_plugin_for_role
from features.local_rendering.vst_registry_schema import VstPluginEntry, VstRegistry


def test_vst_match_prefers_role_and_category() -> None:
    registry = VstRegistry(
        plugins=[
            VstPluginEntry(
                plugin_id="bass_a",
                display_name="Bass A",
                category="bass",
                roles=["bass"],
                available=True,
            ),
            VstPluginEntry(
                plugin_id="lead_a",
                display_name="Lead A",
                category="lead",
                roles=["lead"],
                available=True,
            ),
        ]
    )
    plugin = match_plugin_for_role(registry, track_role="bass", preferred_category="bass")
    assert plugin is not None
    assert plugin.plugin_id == "bass_a"
