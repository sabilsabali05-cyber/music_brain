from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from features.ableton_agent.ableton_command_schema import AbletonCommand
from features.ableton_agent.ableton_intent_schema import AbletonIntent
from features.ableton_agent.ableton_project_state_schema import AbletonProjectState


@dataclass
class AbletonChangePlan:
    interpreted_musical_intent: str
    proposed_arrangement_changes: list[str] = field(default_factory=list)
    proposed_generated_candidates_needed: list[dict[str, Any]] = field(default_factory=list)
    proposed_ableton_commands: list[AbletonCommand] = field(default_factory=list)
    risk_warnings: list[str] = field(default_factory=list)
    human_review_checklist: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "interpreted_musical_intent": self.interpreted_musical_intent,
            "proposed_arrangement_changes": list(self.proposed_arrangement_changes),
            "proposed_generated_candidates_needed": list(self.proposed_generated_candidates_needed),
            "proposed_ableton_commands": [command.to_dict() for command in self.proposed_ableton_commands],
            "risk_warnings": list(self.risk_warnings),
            "human_review_checklist": list(self.human_review_checklist),
        }


def build_ableton_change_plan(
    intent: AbletonIntent,
    project_state: AbletonProjectState,
) -> AbletonChangePlan:
    section_labels = [section.label for section in project_state.arrangement_sections]
    first_track = project_state.tracks[0].track_name if project_state.tracks else "Music Track"
    candidate_id = (
        project_state.available_generated_candidates[0]["candidate_id"]
        if project_state.available_generated_candidates
        else "bridge_candidate_001"
    )
    arrangement_changes = [
        f"Target sections for edits: {', '.join(intent.preferred_sections or section_labels[:2] or ['arrangement'])}.",
        "Reserve an 8-bar bridge lane for candidate insertion and transition shaping.",
        "Preserve existing chorus anchors while previewing structural changes in dry-run only.",
    ]
    commands = [
        AbletonCommand(
            command_type="insert_generated_bridge",
            parameters={
                "target_track": first_track,
                "target_section": (intent.preferred_sections[0] if intent.preferred_sections else "bridge"),
                "candidate_id": candidate_id,
                "candidate_provenance": {
                    "provider": "symbolic_model_placeholder",
                    "artifact_ref": "generated_candidate://" + candidate_id,
                    "status": "generated_candidate",
                },
                "source_material_type": "transcribed",
                "evidence_role": "witness_not_truth",
            },
            generated_candidate=True,
            human_review_required=True,
        ),
        AbletonCommand(
            command_type="thin_arrangement",
            parameters={
                "target_section": (intent.preferred_sections[-1] if intent.preferred_sections else "chorus"),
                "mode": "mute_support_layers",
            },
            human_review_required=True,
        ),
        AbletonCommand(
            command_type="set_track_volume",
            parameters={"track_name": first_track, "value": 1.2},
            human_review_required=True,
        ),
        AbletonCommand(
            command_type="automate_device_parameter",
            parameters={
                "track_name": first_track,
                "device_name": "Unknown_Device_X",
                "parameter_name": "Macro 9",
                "points": [{"bar": 33.0, "value": -0.1}, {"bar": 41.0, "value": 1.4}],
            },
            human_review_required=True,
        ),
    ]
    return AbletonChangePlan(
        interpreted_musical_intent=intent.goal,
        proposed_arrangement_changes=arrangement_changes,
        proposed_generated_candidates_needed=[
            {
                "candidate_id": candidate_id,
                "candidate_type": "bridge",
                "required": True,
                "status": "generated_candidate_not_final",
            }
        ],
        proposed_ableton_commands=commands,
        risk_warnings=[
            "Dry-run only; no real Ableton connection or Live Set mutation.",
            "Destructive changes (thin_arrangement) require explicit human review.",
            "Unknown device/parameter targets are warnings for review, not execution success.",
        ],
        human_review_checklist=[
            "Verify generated candidate provenance before approval.",
            "Confirm arrangement edits are musically appropriate.",
            "Confirm no private local paths are present in reports.",
            "Confirm real execution remains disabled.",
        ],
    )
