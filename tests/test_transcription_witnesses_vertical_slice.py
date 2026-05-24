from __future__ import annotations

import json
from pathlib import Path

from features.model_integrations.model_policy import model_usage_policy, transcription_witness_policy_state
from scripts import (
    check_transcription_witnesses_setup,
    plan_transcription_witnesses,
    run_transcription_witnesses_smoke_tests,
)


def _write_config(path: Path, yourmt3: dict[str, object], basic_pitch: dict[str, object]) -> None:
    payload = {
        "config_version": 1,
        "models": {
            "yourmt3": yourmt3,
            "basic_pitch": basic_pitch,
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def test_transcription_policy_state_defaults() -> None:
    payload = transcription_witness_policy_state()
    assert payload["yourmt3_available"] is False
    assert payload["basic_pitch_available"] is False
    assert payload["transcription_performed"] is False
    assert payload["model_training_has_occurred"] is False
    assert payload["witness_policy"] == "witness_not_truth"


def test_setup_checker_default_unavailable_safe(monkeypatch, tmp_path: Path) -> None:
    example_path = tmp_path / "config" / "model_integrations" / "model_integrations.example.json"
    _write_config(
        example_path,
        {"enabled": False, "model_path": "<PATH_TO_MODEL>", "repo_path": "<PATH_TO_REPO>", "device": "<DEVICE>"},
        {"enabled": False, "model_path": "<PATH_TO_MODEL>", "repo_path": "<PATH_TO_REPO>", "device": "<DEVICE>"},
    )
    monkeypatch.setattr(check_transcription_witnesses_setup, "EXAMPLE_CONFIG", example_path)
    monkeypatch.setattr(check_transcription_witnesses_setup, "LOCAL_CONFIG", tmp_path / "missing.local.json")
    payload = check_transcription_witnesses_setup.evaluate_transcription_witnesses_setup()
    assert payload["yourmt3_available"] is False
    assert payload["basic_pitch_available"] is False
    assert payload["transcription_performed"] is False
    assert payload["model_training_has_occurred"] is False
    assert payload["witness_policy"] == "witness_not_truth"
    assert payload["no_fake_transcription_outputs"] is True


def test_smoke_tests_do_not_transcribe_or_fake_outputs(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(check_transcription_witnesses_setup, "EXAMPLE_CONFIG", tmp_path / "missing.example.json")
    monkeypatch.setattr(check_transcription_witnesses_setup, "LOCAL_CONFIG", tmp_path / "missing.local.json")
    payload = run_transcription_witnesses_smoke_tests.run_transcription_witnesses_smoke_tests()
    assert payload["smoke_test_passed"] is False
    assert payload["transcription_performed"] is False
    assert payload["audio_processing_performed"] is False
    assert payload["downloads_performed"] is False
    assert payload["transcription_outputs_generated"] == []
    notes = " ".join(payload["smoke_test_notes"]).lower()
    assert "no audio processing" in notes
    assert "no transcription execution" in notes


def test_plan_is_plan_only_and_witness_not_truth() -> None:
    payload = plan_transcription_witnesses.build_transcription_witness_plan()
    assert payload["status"] == "planned"
    assert payload["transcription_performed"] is False
    assert payload["audio_processing_performed"] is False
    assert payload["model_training_has_occurred"] is False
    assert payload["witness_policy"] == "witness_not_truth"
    assert payload["no_fake_transcription_outputs"] is True


def test_model_usage_policy_marks_transcription_witnesses() -> None:
    yourmt3_decision = model_usage_policy("yourmt3")
    basic_pitch_decision = model_usage_policy("basic_pitch")
    assert yourmt3_decision.allowed is True
    assert basic_pitch_decision.allowed is True
    assert "witness_not_truth" in yourmt3_decision.tags
    assert "witness_not_truth" in basic_pitch_decision.tags


def test_reports_are_path_safe(tmp_path: Path) -> None:
    json_path, md_path, _ = check_transcription_witnesses_setup.write_transcription_witnesses_setup_report(
        tmp_path / "reports" / "model_integrations"
    )
    assert ("C:/" + "Users/") not in json_path.read_text(encoding="utf-8")
    assert ("C:\\" + "Users\\") not in md_path.read_text(encoding="utf-8")
