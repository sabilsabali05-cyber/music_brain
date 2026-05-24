from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

MidiFxRole = Literal[
    "chord_pattern_generator",
    "arpeggiator",
    "rhythmizer",
    "chord_voicing_transformer",
    "midi_humanizer",
    "generative_midi_effect",
]


@dataclass
class MidiFxTransformPlan:
    generation_id: str
    input_harmony_midi: str
    input_bass_midi: str
    input_lead_guide_midi: str
    output_transformed_midi: str
    bpm: int = 100
    midi_fx_role: MidiFxRole = "chord_pattern_generator"
    midi_fx_plugin_id: str = ""
    chordpotion_configured: bool = False
    chordpotion_available: bool = False
    reaper_available: bool = False
    instrument_vst_available: bool = False
    transformed_midi_captured: bool = False
    blocked: bool = False
    blocked_reason: str = ""
    missing_config: list[str] = field(default_factory=list)
    planner_notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def write_midi_fx_transform_plan(path: Path, plan: MidiFxTransformPlan) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan.as_dict(), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

