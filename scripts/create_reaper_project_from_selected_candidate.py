from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.local_rendering.reaper_backend import load_local_render_config  # noqa: E402
from features.local_rendering.synplant_assignment import assign_synplant_for_intent  # noqa: E402
from features.local_rendering.vst_registry_schema import load_registry  # noqa: E402

GENERATION_ID = "complete_song_v1"
PROJECT_DIR = ROOT_DIR / "outputs" / "reaper_projects" / GENERATION_ID
PROJECT_PATH = PROJECT_DIR / f"{GENERATION_ID}.RPP"
REPORT_JSON = ROOT_DIR / "reports" / "local_rendering" / "reaper_project_creation.json"
REPORT_MD = ROOT_DIR / "reports" / "local_rendering" / "reaper_project_creation.md"


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT_DIR.resolve()).as_posix()
    except Exception:  # noqa: BLE001
        return path.as_posix()


def _resolve_midi_map(stems_dir: Path, transformed_harmony: Path) -> dict[str, str]:
    chords_source = transformed_harmony if transformed_harmony.exists() else stems_dir / "skeleton.mid"
    texture_source = stems_dir / "texture.mid"
    if not texture_source.exists():
        texture_source = stems_dir / "lead.mid"
    return {
        "bass": _repo_rel(stems_dir / "bass.mid"),
        "chords": _repo_rel(chords_source),
        "lead": _repo_rel(stems_dir / "lead.mid"),
        "texture": _repo_rel(texture_source),
    }


def create_reaper_project() -> tuple[Path, dict[str, Any]]:
    local_config = load_local_render_config(ROOT_DIR / "config" / "local_render_config.local.json")
    registry = load_registry(ROOT_DIR / "config" / "local_vst_registry.local.json")
    stems_dir = ROOT_DIR / "outputs" / GENERATION_ID / "stems"
    transformed_harmony = ROOT_DIR / "outputs" / GENERATION_ID / "transformed_harmony.mid"

    preferred_synplant_plugin_id = str(local_config.get("preferred_synplant_plugin_id", "")).strip()
    synplant_enabled = bool(local_config.get("synplant_enabled", False))
    synplant_plugin = registry.get_plugin(preferred_synplant_plugin_id) if preferred_synplant_plugin_id else None
    synplant_configured = bool(synplant_enabled and preferred_synplant_plugin_id)
    synplant_available = bool(synplant_plugin and synplant_plugin.available)

    chordpotion_id = str(local_config.get("preferred_chordpotion_plugin_id", "")).strip()
    chordpotion_plugin = registry.get_plugin(chordpotion_id) if chordpotion_id else None
    chordpotion_available = bool(chordpotion_plugin and chordpotion_plugin.available and chordpotion_plugin.category == "midi_fx")

    midi_map = _resolve_midi_map(stems_dir, transformed_harmony)
    bass_role_configured = bool(str(local_config.get("synplant_bass_preset", "")).strip())
    assignments = {
        "chords": assign_synplant_for_intent(
            texture_intent="warm_emotional_chord_bed",
            track_role="chords",
            synplant_enabled=synplant_enabled,
            synplant_available=synplant_available,
            bass_role_configured=bass_role_configured,
        ),
        "bass": assign_synplant_for_intent(
            texture_intent="bass_motion_driven",
            track_role="bass",
            synplant_enabled=synplant_enabled,
            synplant_available=synplant_available,
            bass_role_configured=bass_role_configured,
        ),
        "lead": assign_synplant_for_intent(
            texture_intent="weird_but_musical",
            track_role="lead",
            synplant_enabled=synplant_enabled,
            synplant_available=synplant_available,
            bass_role_configured=bass_role_configured,
        ),
        "texture": assign_synplant_for_intent(
            texture_intent="haunted_noise_tail",
            track_role="texture",
            synplant_enabled=synplant_enabled,
            synplant_available=synplant_available,
            bass_role_configured=bass_role_configured,
        ),
    }

    PROJECT_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "<REAPER_PROJECT 0.1 \"7.x\" 16909060",
        "  RIPPLE 0",
        "  GROUPOVERRIDE 0 0 0",
        "  ENVATTACH 3",
        "  RENDER_FILE \"outputs/reaper_projects/complete_song_v1\"",
        "  RENDER_PATTERN \"final\"",
        "  RENDER_FMT 0 2 44100",
        "  <TRACK {00000000-0000-0000-0000-000000000101}",
        "    NAME \"Bass\"",
        f"    NOTES \"midi={midi_map['bass']}\"",
        f"    NOTES \"plugin={(preferred_synplant_plugin_id if assignments['bass'].use_synplant else 'fallback_bass')}\"",
        "  >",
        "  <TRACK {00000000-0000-0000-0000-000000000102}",
        "    NAME \"Chords\"",
        f"    NOTES \"midi={midi_map['chords']}\"",
        f"    NOTES \"midi_fx={(chordpotion_id if chordpotion_available else 'none')}\"",
        f"    NOTES \"instrument={(preferred_synplant_plugin_id if assignments['chords'].use_synplant else 'fallback_keys')}\"",
        "  >",
        "  <TRACK {00000000-0000-0000-0000-000000000103}",
        "    NAME \"Lead\"",
        f"    NOTES \"midi={midi_map['lead']}\"",
        f"    NOTES \"plugin={(preferred_synplant_plugin_id if assignments['lead'].use_synplant else 'fallback_lead')}\"",
        "  >",
        "  <TRACK {00000000-0000-0000-0000-000000000104}",
        "    NAME \"Texture\"",
        f"    NOTES \"midi={midi_map['texture']}\"",
        f"    NOTES \"plugin={(preferred_synplant_plugin_id if assignments['texture'].use_synplant else 'fallback_texture')}\"",
        "  >",
        ">",
    ]
    PROJECT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    blockers: list[str] = []
    if not stems_dir.exists():
        blockers.append("stems_directory_missing")
    if not synplant_configured:
        blockers.append("preferred_synplant_plugin_id_or_synplant_enabled_missing")
    elif not synplant_available:
        blockers.append("synplant_plugin_unavailable")
    if not chordpotion_available:
        blockers.append("chordpotion_optional_midi_fx_unavailable")

    payload = {
        "generation_id": GENERATION_ID,
        "reaper_project_path": _repo_rel(PROJECT_PATH),
        "reaper_project_created": PROJECT_PATH.exists(),
        "chordpotion_can_route_into_synplant": bool(chordpotion_available and assignments["chords"].use_synplant),
        "synplant_configured": synplant_configured,
        "synplant_available": synplant_available,
        "synplant_is_render_target_only": True,
        "synplant_is_not_composer": True,
        "assignments": {
            key: {
                "texture_intent": assignment.texture_intent,
                "use_synplant": assignment.use_synplant,
                "target_role": assignment.target_role,
                "fallback_category": assignment.fallback_category,
                "reason": assignment.reason,
                "is_composer": assignment.is_composer,
            }
            for key, assignment in assignments.items()
        },
        "blockers": blockers,
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    REPORT_MD.write_text(
        "\n".join(
            [
                "# Reaper Project Creation",
                "",
                f"- reaper_project_created: `{str(payload['reaper_project_created']).lower()}`",
                f"- reaper_project_path: `{payload['reaper_project_path']}`",
                f"- synplant_configured: `{str(payload['synplant_configured']).lower()}`",
                f"- synplant_available: `{str(payload['synplant_available']).lower()}`",
                f"- chordpotion_can_route_into_synplant: `{str(payload['chordpotion_can_route_into_synplant']).lower()}`",
                "- synplant_is_not_composer: `true`",
                "",
                "## Blockers",
            ]
            + ([f"- {item}" for item in blockers] if blockers else ["- none"])
            + [""],
        ),
        encoding="utf-8",
    )
    return PROJECT_PATH, payload


def main() -> int:
    project_path, payload = create_reaper_project()
    print(f"REAPER_PROJECT_PATH={_repo_rel(project_path)}")
    print(f"REAPER_PROJECT_CREATED={str(payload['reaper_project_created']).lower()}")
    print(f"SYNPLANT_CONFIGURED={str(payload['synplant_configured']).lower()}")
    print(f"SYNPLANT_AVAILABLE={str(payload['synplant_available']).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
