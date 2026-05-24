from __future__ import annotations

from pathlib import Path

from .vst_registry_schema import VstPluginEntry, VstRegistry

PLUGIN_EXTENSIONS = {
    ".dll": "VST2",
    ".vst3": "VST3",
    ".clap": "CLAP",
    ".adg": "AbletonDevice",
    ".amxd": "M4L",
}


def _redact_local_path(path: Path) -> str:
    return f"<LOCAL>/{path.name}"


def _plugin_id_from_path(path: Path) -> str:
    normalized = path.stem.lower().replace(" ", "_").replace("-", "_")
    return f"local_{normalized}"


def scan_vst_paths(scan_paths: list[str]) -> VstRegistry:
    plugins: list[VstPluginEntry] = []
    seen_ids: set[str] = set()

    for raw_path in scan_paths:
        path = Path(raw_path)
        if not path.exists():
            continue
        if path.is_file():
            candidates = [path]
        else:
            candidates = [item for item in path.rglob("*") if item.is_file()]
        for candidate in candidates:
            extension = candidate.suffix.lower()
            plugin_format = PLUGIN_EXTENSIONS.get(extension)
            if plugin_format is None:
                continue
            plugin_id = _plugin_id_from_path(candidate)
            if plugin_id in seen_ids:
                continue
            seen_ids.add(plugin_id)
            plugins.append(
                VstPluginEntry(
                    plugin_id=plugin_id,
                    display_name=candidate.stem,
                    vendor="unknown_local_vendor",
                    format=plugin_format,  # type: ignore[arg-type]
                    category="instrument",
                    local_path=str(candidate),
                    local_path_redacted=_redact_local_path(candidate),
                    available=True,
                    verified_loadable=False,
                    preset_names=[],
                    texture_tags=[],
                    roles=[],
                    notes="Discovered by filename scan only; loadability not guaranteed.",
                )
            )

    return VstRegistry(plugins=plugins, registry_source="filesystem_scan")
