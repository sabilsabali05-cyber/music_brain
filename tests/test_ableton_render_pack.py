from __future__ import annotations

from pathlib import Path

from features.local_rendering.ableton_backend import create_ableton_assisted_render_pack
from features.local_rendering.render_plan_schema import RenderPlan


def test_ableton_pack_created_when_requested(tmp_path: Path) -> None:
    stems_dir = tmp_path / "stems"
    stems_dir.mkdir(parents=True, exist_ok=True)
    (stems_dir / "lead.mid").write_bytes(b"MThd")
    report = create_ableton_assisted_render_pack(
        generation_id="g1",
        stems_dir=stems_dir,
        plan=RenderPlan(generation_id="g1", default_render_backend="ableton_assisted_render", stems=[]),
        reason="reaper_unavailable",
    )
    assert report.render_backend_status == "assisted_pack_created"
    assert report.wav_rendered is False
    assert report.render_plan_only is True
