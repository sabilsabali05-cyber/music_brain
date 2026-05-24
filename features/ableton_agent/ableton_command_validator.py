from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from features.ableton_agent.ableton_command_schema import (
    AUTOMATION_COMMANDS,
    DESTRUCTIVE_COMMANDS,
    MODEL_GENERATED_COMMANDS,
    PLANNED_FUTURE_COMMANDS,
    AbletonCommand,
)
from features.ableton_agent.ableton_project_state_schema import AbletonProjectState


@dataclass
class AbletonCommandValidationResult:
    valid: bool
    sanitized_commands: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    human_review_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "sanitized_commands": list(self.sanitized_commands),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "human_review_required": self.human_review_required,
        }


def _clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def _clamp_automation(command: AbletonCommand, warnings: list[str]) -> None:
    if command.command_type == "set_track_volume":
        raw = float(command.parameters.get("value", 0.8))
        clamped = _clamp(raw, 0.0, 1.0)
        command.parameters["value"] = clamped
        if clamped != raw:
            warnings.append(f"Clamped set_track_volume from {raw} to {clamped}.")
    elif command.command_type == "set_track_pan":
        raw = float(command.parameters.get("value", 0.0))
        clamped = _clamp(raw, -1.0, 1.0)
        command.parameters["value"] = clamped
        if clamped != raw:
            warnings.append(f"Clamped set_track_pan from {raw} to {clamped}.")
    elif command.command_type in {"automate_device_parameter", "automate_mixer_parameter"}:
        points = command.parameters.get("points", [])
        safe_points: list[dict[str, float]] = []
        for idx, row in enumerate(points):
            value = float(row.get("value", 0.0))
            clamped = _clamp(value, 0.0, 1.0)
            safe_points.append({"bar": float(row.get("bar", 0.0)), "value": clamped})
            if clamped != value:
                warnings.append(
                    f"Clamped {command.command_type} point {idx} value from {value} to {clamped}."
                )
        command.parameters["points"] = safe_points
    elif command.command_type == "create_return_send_automation":
        raw = float(command.parameters.get("send_amount", 0.0))
        clamped = _clamp(raw, 0.0, 1.0)
        command.parameters["send_amount"] = clamped
        if clamped != raw:
            warnings.append(f"Clamped create_return_send_automation from {raw} to {clamped}.")


def validate_ableton_commands(
    commands: list[AbletonCommand],
    project_state: AbletonProjectState,
) -> AbletonCommandValidationResult:
    warnings: list[str] = []
    errors: list[str] = []
    sanitized: list[dict[str, Any]] = []

    known_devices = {device.device_name for device in project_state.devices}
    known_parameters = set(project_state.parameters)

    for command in commands:
        if command.command_type not in PLANNED_FUTURE_COMMANDS:
            errors.append(f"Unknown command_type: {command.command_type}")
            continue

        if command.command_type in DESTRUCTIVE_COMMANDS and not command.human_review_required:
            errors.append(
                f"Destructive command `{command.command_type}` must set human_review_required=true."
            )

        if command.command_type in MODEL_GENERATED_COMMANDS:
            if not command.generated_candidate:
                errors.append(
                    f"{command.command_type} must be marked generated_candidate=true."
                )
            if not command.parameters.get("candidate_provenance"):
                errors.append(
                    f"{command.command_type} requires candidate_provenance metadata."
                )

        if command.parameters.get("source_material_type") in {"source_separated", "transcribed"}:
            evidence_role = str(command.parameters.get("evidence_role", "")).strip()
            if evidence_role != "witness_not_truth":
                errors.append(
                    f"{command.command_type} with {command.parameters['source_material_type']} material must mark evidence_role=witness_not_truth."
                )

        if command.command_type in AUTOMATION_COMMANDS:
            _clamp_automation(command, warnings)

        if command.command_type == "automate_device_parameter":
            device_name = str(command.parameters.get("device_name", ""))
            parameter_name = str(command.parameters.get("parameter_name", ""))
            if device_name and device_name not in known_devices:
                warnings.append(
                    f"Unknown device `{device_name}`; command kept as warning for manual review."
                )
            if parameter_name and parameter_name not in known_parameters:
                warnings.append(
                    f"Unknown parameter `{parameter_name}`; command kept as warning for manual review."
                )

        sanitized.append(command.to_dict())

    valid = not errors
    return AbletonCommandValidationResult(
        valid=valid,
        sanitized_commands=sanitized,
        warnings=warnings,
        errors=errors,
        human_review_required=True,
    )
