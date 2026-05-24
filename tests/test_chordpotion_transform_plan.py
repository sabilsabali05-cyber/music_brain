from __future__ import annotations

from features.local_rendering.chordpotion_transform_plan import render_chordpotion_transform_plan_markdown
from features.local_rendering.midi_fx_schema import MidiFxTransformPlan


def test_transform_plan_markdown_includes_honest_booleans() -> None:
    plan = MidiFxTransformPlan(
        generation_id="chordpotion_generation_v1",
        input_harmony_midi="outputs/chordpotion_generation_v1/harmony_skeleton.mid",
        input_bass_midi="outputs/chordpotion_generation_v1/bass.mid",
        input_lead_guide_midi="outputs/chordpotion_generation_v1/lead_guide.mid",
        output_transformed_midi="outputs/chordpotion_generation_v1/transformed_harmony.mid",
        chordpotion_configured=False,
        chordpotion_available=False,
        reaper_available=False,
        instrument_vst_available=False,
        transformed_midi_captured=False,
        blocked=True,
        blocked_reason="local_requirements_missing",
        missing_config=["reaper_executable_path"],
    )
    markdown = render_chordpotion_transform_plan_markdown(plan)
    assert "chordpotion_configured: `false`" in markdown
    assert "blocked: `true`" in markdown
    assert "transformed_midi_captured: `false`" in markdown

