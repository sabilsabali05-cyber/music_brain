from __future__ import annotations

from pathlib import Path

from features.local_rendering.render_plan_schema import RenderPlan, RenderPlanStem, read_render_plan_json, write_render_plan_json


def test_render_plan_roundtrip(tmp_path: Path) -> None:
    plan = RenderPlan(
        generation_id="g1",
        default_render_backend="dry_run_plan_only",
        stems=[
            RenderPlanStem(
                midi_path="outputs/g1/stems/lead.mid",
                track_name="lead",
                track_role="lead",
                texture_intent="foreground melodic clarity",
                render_backend="dry_run_plan_only",
            )
        ],
    )
    path = tmp_path / "plan.json"
    write_render_plan_json(path, plan)
    loaded = read_render_plan_json(path)
    assert loaded.generation_id == "g1"
    assert loaded.stems[0].track_role == "lead"
