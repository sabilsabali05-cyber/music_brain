from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .midi_fx_schema import MidiFxTransformPlan


def write_chordpotion_transform_plan(path: Path, plan: MidiFxTransformPlan) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(plan), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def render_chordpotion_transform_plan_markdown(plan: MidiFxTransformPlan) -> str:
    lines = [
        "# ChordPotion Transform Plan",
        "",
        f"- generation_id: `{plan.generation_id}`",
        f"- bpm: `{plan.bpm}`",
        f"- midi_fx_role: `{plan.midi_fx_role}`",
        f"- midi_fx_plugin_id: `{plan.midi_fx_plugin_id or 'none'}`",
        f"- chordpotion_configured: `{str(plan.chordpotion_configured).lower()}`",
        f"- chordpotion_available: `{str(plan.chordpotion_available).lower()}`",
        f"- reaper_available: `{str(plan.reaper_available).lower()}`",
        f"- instrument_vst_available: `{str(plan.instrument_vst_available).lower()}`",
        f"- transformed_midi_captured: `{str(plan.transformed_midi_captured).lower()}`",
        f"- blocked: `{str(plan.blocked).lower()}`",
        f"- blocked_reason: `{plan.blocked_reason or 'none'}`",
        "",
        "## Inputs/Outputs",
        f"- input_harmony_midi: `{plan.input_harmony_midi}`",
        f"- input_bass_midi: `{plan.input_bass_midi}`",
        f"- input_lead_guide_midi: `{plan.input_lead_guide_midi}`",
        f"- output_transformed_midi: `{plan.output_transformed_midi}`",
        "",
        "## Missing Config",
    ]
    lines.extend([f"- {item}" for item in plan.missing_config] or ["- none"])
    lines.extend(["", "## Planner Notes"])
    lines.extend([f"- {item}" for item in plan.planner_notes] or ["- none"])
    lines.append("")
    return "\n".join(lines)

