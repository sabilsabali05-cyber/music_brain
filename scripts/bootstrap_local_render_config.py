from __future__ import annotations

import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def _write_if_missing(path: Path, payload: dict) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return True


def main() -> int:
    local_render_config = ROOT_DIR / "config" / "local_render_config.local.json"
    local_vst_registry = ROOT_DIR / "config" / "local_vst_registry.local.json"

    render_payload = {
        "reaper_executable_path": "",
        "ableton_executable_path": "",
        "default_render_backend": "dry_run_plan_only",
        "render_sample_rate": 48000,
        "render_bit_depth": 24,
        "render_stems": True,
        "vst_scan_paths": [],
        "preferred_piano_plugin_id": "",
        "preferred_pad_plugin_id": "",
        "preferred_bass_plugin_id": "",
        "preferred_lead_plugin_id": "",
        "preferred_texture_plugin_id": "",
        "preferred_drum_plugin_id": "",
        "preferred_chordpotion_plugin_id": "",
        "preferred_synplant_plugin_id": "",
        "chordpotion_plugin_id": "",
        "chordpotion_default_bpm": 100,
        "chordpotion_capture_transformed_midi": False,
        "chordpotion_assisted_pack_output_dir": "outputs/render_ready_packs",
        "synplant_enabled": False,
        "synplant_default_preset": "",
        "synplant_pad_preset": "",
        "synplant_lead_preset": "",
        "synplant_bass_preset": "",
        "synplant_texture_preset": "",
        "preferred_reverb_effect_id": "",
        "preferred_delay_effect_id": "",
        "preferred_distortion_effect_id": "",
    }
    vst_payload = {
        "registry_source": "local_private_template",
        "plugins": [],
    }

    created_render = _write_if_missing(local_render_config, render_payload)
    created_registry = _write_if_missing(local_vst_registry, vst_payload)
    print(f"LOCAL_RENDER_CONFIG_CREATED={str(created_render).lower()}")
    print(f"LOCAL_VST_REGISTRY_CREATED={str(created_registry).lower()}")
    print(f"LOCAL_RENDER_CONFIG_PATH={local_render_config.as_posix()}")
    print(f"LOCAL_VST_REGISTRY_PATH={local_vst_registry.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
