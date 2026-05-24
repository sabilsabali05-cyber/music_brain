from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

PluginFormat = Literal["VST2", "VST3", "CLAP", "AbletonDevice", "M4L"]
ALLOWED_PLUGIN_CATEGORIES = {"instrument", "effect", "keys", "bass", "lead", "pad", "drums", "texture", "midi_fx"}
MIDI_FX_ROLES = {
    "chord_pattern_generator",
    "arpeggiator",
    "rhythmizer",
    "chord_voicing_transformer",
    "midi_humanizer",
    "generative_midi_effect",
}


@dataclass
class VstPluginEntry:
    plugin_id: str
    display_name: str
    vendor: str = ""
    format: PluginFormat = "VST3"
    category: str = "instrument"
    local_path: str = ""
    local_path_redacted: str = "local_only"
    available: bool = False
    verified_loadable: bool = False
    preset_names: list[str] = field(default_factory=list)
    texture_tags: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    notes: str = ""

    def to_public_dict(self) -> dict:
        payload = asdict(self)
        payload["local_path"] = ""
        return payload


@dataclass
class VstRegistry:
    plugins: list[VstPluginEntry] = field(default_factory=list)
    registry_source: str = "manual_or_scanned"

    @property
    def configured(self) -> bool:
        return len(self.plugins) > 0

    def get_plugin(self, plugin_id: str) -> VstPluginEntry | None:
        for plugin in self.plugins:
            if plugin.plugin_id == plugin_id:
                return plugin
        return None

    def available_plugins(self) -> list[VstPluginEntry]:
        return [plugin for plugin in self.plugins if plugin.available]

    def to_public_dict(self) -> dict:
        return {
            "registry_source": self.registry_source,
            "plugins": [plugin.to_public_dict() for plugin in self.plugins],
        }

    def to_local_dict(self) -> dict:
        return {
            "registry_source": self.registry_source,
            "plugins": [asdict(plugin) for plugin in self.plugins],
        }


def _parse_plugin(payload: dict) -> VstPluginEntry:
    plugin_format = str(payload.get("format", "VST3"))
    if plugin_format not in {"VST2", "VST3", "CLAP", "AbletonDevice", "M4L"}:
        plugin_format = "VST3"
    category = str(payload.get("category", "instrument")).strip() or "instrument"
    if category not in ALLOWED_PLUGIN_CATEGORIES:
        category = "instrument"
    roles = [str(item) for item in payload.get("roles", []) if str(item).strip()]
    if category == "midi_fx":
        # Keep midi-fx role vocabulary bounded for deterministic matching and reports.
        roles = [role for role in roles if role in MIDI_FX_ROLES] or ["generative_midi_effect"]
    return VstPluginEntry(
        plugin_id=str(payload.get("plugin_id", "")),
        display_name=str(payload.get("display_name", "")),
        vendor=str(payload.get("vendor", "")),
        format=plugin_format,  # type: ignore[arg-type]
        category=category,
        local_path=str(payload.get("local_path", "")),
        local_path_redacted=str(payload.get("local_path_redacted", "local_only")),
        available=bool(payload.get("available", False)),
        verified_loadable=bool(payload.get("verified_loadable", False)),
        preset_names=[str(item) for item in payload.get("preset_names", []) if str(item).strip()],
        texture_tags=[str(item) for item in payload.get("texture_tags", []) if str(item).strip()],
        roles=roles,
        notes=str(payload.get("notes", "")),
    )


def load_registry(path: Path) -> VstRegistry:
    if not path.exists():
        return VstRegistry(plugins=[], registry_source="missing")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return VstRegistry(plugins=[], registry_source="invalid_json")
    if not isinstance(payload, dict):
        return VstRegistry(plugins=[], registry_source="invalid_schema")
    plugins_raw = payload.get("plugins", [])
    if not isinstance(plugins_raw, list):
        plugins_raw = []
    plugins = [_parse_plugin(item) for item in plugins_raw if isinstance(item, dict)]
    source = str(payload.get("registry_source", "manual_or_scanned"))
    return VstRegistry(plugins=plugins, registry_source=source)


def write_registry_public(path: Path, registry: VstRegistry) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry.to_public_dict(), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def write_registry_local(path: Path, registry: VstRegistry) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry.to_local_dict(), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
