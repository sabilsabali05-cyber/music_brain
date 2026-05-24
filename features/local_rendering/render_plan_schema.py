from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

RenderBackend = Literal[
    "reaper_auto_render",
    "ableton_assisted_render",
    "preview_synth_render",
    "dry_run_plan_only",
]


@dataclass
class RenderPlanStem:
    midi_path: str
    track_name: str
    track_role: str
    texture_intent: str
    suggested_plugin_id: str = ""
    suggested_preset: str = ""
    fallback_plugin_category: str = ""
    effect_chain: list[str] = field(default_factory=list)
    register_adjustment: str = "none"
    velocity_adjustment: str = "none"
    expected_ear_effect: str = ""
    render_backend: RenderBackend = "dry_run_plan_only"
    uncertainty: str = "medium"
    manual_notes: list[str] = field(default_factory=list)


@dataclass
class RenderPlan:
    generation_id: str
    default_render_backend: RenderBackend
    stems: list[RenderPlanStem] = field(default_factory=list)
    planner_notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def write_render_plan_json(path: Path, plan: RenderPlan) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan.as_dict(), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def read_render_plan_json(path: Path) -> RenderPlan:
    if not path.exists():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    stems_raw = payload.get("stems", [])
    stems: list[RenderPlanStem] = []
    for item in stems_raw:
        if not isinstance(item, dict):
            continue
        stems.append(
            RenderPlanStem(
                midi_path=str(item.get("midi_path", "")),
                track_name=str(item.get("track_name", "")),
                track_role=str(item.get("track_role", "")),
                texture_intent=str(item.get("texture_intent", "")),
                suggested_plugin_id=str(item.get("suggested_plugin_id", "")),
                suggested_preset=str(item.get("suggested_preset", "")),
                fallback_plugin_category=str(item.get("fallback_plugin_category", "")),
                effect_chain=[str(x) for x in item.get("effect_chain", []) if str(x).strip()],
                register_adjustment=str(item.get("register_adjustment", "none")),
                velocity_adjustment=str(item.get("velocity_adjustment", "none")),
                expected_ear_effect=str(item.get("expected_ear_effect", "")),
                render_backend=str(item.get("render_backend", "dry_run_plan_only")),  # type: ignore[arg-type]
                uncertainty=str(item.get("uncertainty", "medium")),
                manual_notes=[str(x) for x in item.get("manual_notes", []) if str(x).strip()],
            )
        )
    return RenderPlan(
        generation_id=str(payload.get("generation_id", "")),
        default_render_backend=str(payload.get("default_render_backend", "dry_run_plan_only")),  # type: ignore[arg-type]
        stems=stems,
        planner_notes=[str(x) for x in payload.get("planner_notes", []) if str(x).strip()],
    )


def render_plan_markdown(plan: RenderPlan) -> str:
    lines = [
        "# Local Render Plan",
        "",
        f"- generation_id: `{plan.generation_id}`",
        f"- default_render_backend: `{plan.default_render_backend}`",
        "",
        "## Stem Assignments",
    ]
    if not plan.stems:
        lines.append("- none")
    for stem in plan.stems:
        lines.append(
            f"- `{stem.track_name}` role=`{stem.track_role}` plugin=`{stem.suggested_plugin_id or 'none'}` "
            f"preset=`{stem.suggested_preset or 'none'}` backend=`{stem.render_backend}` uncertainty=`{stem.uncertainty}`"
        )
    lines.extend(["", "## Planner Notes"])
    lines.extend([f"- {note}" for note in plan.planner_notes] or ["- none"])
    lines.append("")
    return "\n".join(lines)
