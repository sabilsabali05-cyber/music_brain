from __future__ import annotations

import json
from pathlib import Path

from features.local_rendering.vst_registry_schema import VstPluginEntry, VstRegistry, write_registry_public


def test_public_registry_redacts_local_path(tmp_path: Path) -> None:
    registry = VstRegistry(
        plugins=[
            VstPluginEntry(
                plugin_id="piano_1",
                display_name="Private Piano",
                local_path="C:/private/path/Private Piano.vst3",
                local_path_redacted="<LOCAL>/Private Piano.vst3",
                available=True,
            )
        ]
    )
    output = tmp_path / "registry.public.json"
    write_registry_public(output, registry)
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["plugins"][0]["local_path"] == ""
    assert payload["plugins"][0]["local_path_redacted"] == "<LOCAL>/Private Piano.vst3"
