from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, get_args

AbletonCommandName = Literal[
    "create_track",
    "create_midi_clip",
    "replace_midi_clip",
    "duplicate_clip",
    "move_clip",
    "split_section",
    "create_scene",
    "rename_track",
    "group_tracks",
    "set_track_volume",
    "set_track_pan",
    "automate_device_parameter",
    "automate_mixer_parameter",
    "add_device_placeholder",
    "route_track_placeholder",
    "create_return_send_automation",
    "insert_generated_bridge",
    "insert_generated_variation",
    "thin_arrangement",
    "build_transition",
    "export_review_package",
]

PLANNED_FUTURE_COMMANDS: tuple[str, ...] = get_args(AbletonCommandName)

DESTRUCTIVE_COMMANDS: set[str] = {
    "replace_midi_clip",
    "move_clip",
    "split_section",
    "thin_arrangement",
}

MODEL_GENERATED_COMMANDS: set[str] = {
    "insert_generated_bridge",
    "insert_generated_variation",
}

AUTOMATION_COMMANDS: set[str] = {
    "set_track_volume",
    "set_track_pan",
    "automate_device_parameter",
    "automate_mixer_parameter",
    "create_return_send_automation",
}


@dataclass
class AbletonCommand:
    command_type: AbletonCommandName
    parameters: dict[str, Any] = field(default_factory=dict)
    human_review_required: bool = True
    generated_candidate: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "command_type": self.command_type,
            "parameters": self.parameters,
            "human_review_required": self.human_review_required,
            "generated_candidate": self.generated_candidate,
            "notes": self.notes,
        }
