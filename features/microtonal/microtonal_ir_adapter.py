from __future__ import annotations

from typing import Any

from .tuning_registry import get_tuning_preset


def build_microtonal_ir_plan(*, preset_id: str, stems: list[str]) -> dict[str, Any]:
    preset = get_tuning_preset(preset_id)
    return {
        "status": "ok",
        "preset_id": preset.preset_id,
        "placeholder_safe": preset.placeholder_safe,
        "advisory": preset.advisory,
        "stem_plans": [{"stem": stem, "steps_per_octave": preset.steps_per_octave, "interval_count": len(preset.intervals_cents)} for stem in stems],
        "no_audio_generated": True,
        "cloud_called": False,
        "training_performed": False,
    }
