from __future__ import annotations

import json
from pathlib import Path

from features.ableton_agent import (
    PLANNED_FUTURE_COMMANDS,
    AbletonCommand,
    build_ableton_change_plan,
    validate_ableton_commands,
)
from scripts.plan_ableton_agent_change import (
    build_change_plan_payload,
    build_mock_project_state,
    build_sample_intent,
)
from scripts.run_ableton_agent_dry_run import build_dry_run_payload, write_dry_run_report


def test_commands_validate_against_schema_and_list() -> None:
    payload = build_change_plan_payload()
    command_types = {row["command_type"] for row in payload["proposed_ableton_commands"]}
    assert command_types
    assert command_types.issubset(set(PLANNED_FUTURE_COMMANDS))
    assert payload["commands_generated"] is True


def test_destructive_commands_require_review() -> None:
    project_state = build_mock_project_state()
    bad = AbletonCommand(
        command_type="thin_arrangement",
        parameters={"target_section": "chorus_2"},
        human_review_required=False,
    )
    result = validate_ableton_commands([bad], project_state)
    assert result.valid is False
    assert any("must set human_review_required=true" in err for err in result.errors)


def test_no_real_ableton_calls_or_gui_automation_in_reports() -> None:
    payload = build_dry_run_payload()
    assert payload["ableton_connected"] is False
    assert payload["commands_executed"] is False
    assert payload["no_gui_automation"] is True
    assert payload["no_real_ableton_operations"] is True


def test_reports_do_not_contain_private_paths(tmp_path: Path) -> None:
    output_dir = tmp_path / "reports" / "ableton_agent"
    json_path, md_path, _ = write_dry_run_report(output_dir)
    for report_path in (json_path, md_path):
        text = report_path.read_text(encoding="utf-8")
        assert "C:/Users/" not in text
        assert "C:\\Users\\" not in text


def test_dry_run_modifies_no_files_except_reports(tmp_path: Path) -> None:
    output_dir = tmp_path / "reports" / "ableton_agent"
    json_path, md_path, _ = write_dry_run_report(output_dir)
    created_files = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*") if path.is_file())
    assert created_files == sorted(
        [
            json_path.relative_to(tmp_path).as_posix(),
            md_path.relative_to(tmp_path).as_posix(),
        ]
    )


def test_generated_bridge_command_has_candidate_provenance() -> None:
    payload = build_change_plan_payload()
    bridge = next(row for row in payload["proposed_ableton_commands"] if row["command_type"] == "insert_generated_bridge")
    assert bridge["generated_candidate"] is True
    assert bridge["parameters"]["candidate_provenance"]["status"] == "generated_candidate"
    assert bridge["parameters"]["candidate_provenance"]["artifact_ref"].startswith("generated_candidate://")


def test_automation_commands_are_clamped_to_ranges() -> None:
    intent = build_sample_intent()
    state = build_mock_project_state()
    plan = build_ableton_change_plan(intent, state)
    result = validate_ableton_commands(plan.proposed_ableton_commands, state)
    assert result.valid is True
    assert any("Clamped set_track_volume" in warning for warning in result.warnings)
    volume = next(row for row in result.sanitized_commands if row["command_type"] == "set_track_volume")
    assert 0.0 <= float(volume["parameters"]["value"]) <= 1.0
    automate = next(row for row in result.sanitized_commands if row["command_type"] == "automate_device_parameter")
    for point in automate["parameters"]["points"]:
        assert 0.0 <= float(point["value"]) <= 1.0


def test_unknown_devices_or_parameters_warn_not_fake_success() -> None:
    intent = build_sample_intent()
    state = build_mock_project_state()
    plan = build_ableton_change_plan(intent, state)
    result = validate_ableton_commands(plan.proposed_ableton_commands, state)
    assert result.valid is True
    assert any("Unknown device" in warning for warning in result.warnings)
    assert any("Unknown parameter" in warning for warning in result.warnings)


def test_live_set_mutation_and_training_remain_false() -> None:
    payload = build_dry_run_payload()
    assert payload["live_set_modified"] is False
    assert payload["training_performed"] is False
    assert payload["audio_processing_performed"] is False
    assert payload["model_generation_performed"] is False


def test_reports_remain_json_serializable() -> None:
    payload = build_dry_run_payload()
    dumped = json.dumps(payload, ensure_ascii=True)
    assert "\"commands_executed\": false" in dumped
