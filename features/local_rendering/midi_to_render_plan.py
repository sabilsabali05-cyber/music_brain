from __future__ import annotations

from pathlib import Path

from .render_plan_schema import RenderPlan, RenderPlanStem
from .texture_vst_assignment import assign_plugin_for_texture
from .vst_registry_schema import VstRegistry


def _role_from_name(track_name: str) -> str:
    lowered = track_name.lower()
    if "drum" in lowered:
        return "drums"
    if "bass" in lowered:
        return "bass"
    if "pad" in lowered:
        return "pad"
    if "lead" in lowered:
        return "lead"
    if "piano" in lowered or "keys" in lowered:
        return "keys"
    return "texture"


def _texture_from_role(role: str) -> str:
    mapping = {
        "drums": "punchy rhythmic backbone",
        "bass": "supportive low-end pulse",
        "lead": "foreground melodic clarity",
        "pad": "wide atmospheric bed",
        "keys": "harmonic body and motion",
        "texture": "ambient evolving movement",
    }
    return mapping.get(role, "balanced instrumental texture")


def _repo_relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:  # noqa: BLE001
        return path.as_posix()


def build_render_plan_from_stems(
    generation_id: str,
    stems_dir: Path,
    registry: VstRegistry,
    default_backend: str = "dry_run_plan_only",
) -> RenderPlan:
    root = Path(__file__).resolve().parent.parent.parent
    midi_files = sorted([item for item in stems_dir.glob("*.mid") if item.is_file()])
    stems: list[RenderPlanStem] = []
    for midi_file in midi_files:
        track_name = midi_file.stem
        track_role = _role_from_name(track_name)
        texture_intent = _texture_from_role(track_role)
        plugin_id, preset, fallback_category = assign_plugin_for_texture(
            registry=registry,
            track_role=track_role,
            texture_intent=texture_intent,
        )
        effects = ["eq_cleanup", "gentle_compressor"]
        if track_role in {"pad", "texture"}:
            effects.extend(["chorus", "reverb_large"])
        if track_role == "lead":
            effects.extend(["delay_ping_pong", "reverb_plate"])
        if track_role == "drums":
            effects.append("transient_shaper")
        stems.append(
            RenderPlanStem(
                midi_path=_repo_relative(midi_file, root),
                track_name=track_name,
                track_role=track_role,
                texture_intent=texture_intent,
                suggested_plugin_id=plugin_id,
                suggested_preset=preset,
                fallback_plugin_category=fallback_category,
                effect_chain=effects,
                register_adjustment="none",
                velocity_adjustment="humanize_light",
                expected_ear_effect=f"{track_role} supports arrangement balance",
                render_backend=default_backend,  # type: ignore[arg-type]
                uncertainty="medium" if plugin_id else "high",
                manual_notes=[
                    "Confirm MIDI octave/register in DAW.",
                    "Confirm preset gain staging avoids clipping.",
                ],
            )
        )
    notes = [
        "Plan generated from local MIDI stems only.",
        "No cloud render calls or model training were used.",
        "If VST config is missing, backend should remain dry_run_plan_only.",
    ]
    return RenderPlan(
        generation_id=generation_id,
        default_render_backend=default_backend,  # type: ignore[arg-type]
        stems=stems,
        planner_notes=notes,
    )
