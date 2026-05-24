from __future__ import annotations

from pathlib import Path

from features.local_rendering.reaper_backend import run_reaper_auto_render
from features.local_rendering.render_plan_schema import RenderPlan


def test_reaper_backend_safe_fails_when_missing_config(tmp_path: Path) -> None:
    plan = RenderPlan(generation_id="g1", default_render_backend="reaper_auto_render", stems=[])
    report = run_reaper_auto_render(
        generation_id="g1",
        plan=plan,
        reaper_executable_path="",
        vst_registry_configured=False,
        local_render_root=tmp_path / "renders" / "g1",
    )
    assert report.reaper_available is False
    assert report.wav_rendered is False
    assert report.render_plan_only is True
    assert report.render_backend_status == "planned_not_executed"
