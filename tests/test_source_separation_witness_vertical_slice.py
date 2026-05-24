from __future__ import annotations

import json
from pathlib import Path

from features.model_integrations.model_policy import model_usage_policy, source_separation_witness_policy_state
from scripts import check_source_separation_setup, plan_source_separation_witness, run_source_separation_smoke_tests


def _write_config(path: Path, demucs: dict[str, object]) -> None:
    payload = {"config_version": 1, "models": {"demucs": demucs}}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def test_source_separation_policy_defaults() -> None:
    payload = source_separation_witness_policy_state()
    assert payload["demucs_available"] is False
    assert payload["source_separation_performed"] is False
    assert payload["stems_generated"] is False
    assert payload["downloads_performed"] is False
    assert payload["model_training_has_occurred"] is False
    assert payload["witness_policy"] == "weak_evidence_not_truth"


def test_setup_checker_demucs_disabled_by_default(monkeypatch, tmp_path: Path) -> None:
    example_path = tmp_path / "config" / "model_integrations" / "model_integrations.example.json"
    _write_config(
        example_path,
        {
            "enabled": False,
            "package_required": "demucs",
            "model_name": "htdemucs",
            "device": "<DEVICE>",
            "smoke_test_enabled": False,
            "output_dir": "<PATH_TO_REPO>",
            "stem_policy": "weak_evidence_not_truth",
        },
    )
    monkeypatch.setattr(check_source_separation_setup, "EXAMPLE_CONFIG", example_path)
    monkeypatch.setattr(check_source_separation_setup, "LOCAL_CONFIG", tmp_path / "missing.local.json")
    payload = check_source_separation_setup.evaluate_source_separation_setup()
    assert payload["demucs_configured"] is False
    assert payload["demucs_available"] is False
    assert payload["source_separation_performed"] is False
    assert payload["stems_generated"] is False
    assert payload["downloads_performed"] is False
    assert payload["model_training_has_occurred"] is False
    assert payload["witness_policy"] == "weak_evidence_not_truth"
    assert payload["training_use_allowed"] == "false_by_default"


def test_setup_checker_does_not_process_audio(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(check_source_separation_setup, "EXAMPLE_CONFIG", tmp_path / "missing.example.json")
    monkeypatch.setattr(check_source_separation_setup, "LOCAL_CONFIG", tmp_path / "missing.local.json")
    payload = check_source_separation_setup.evaluate_source_separation_setup()
    assert payload["audio_processing_performed"] is False
    assert payload["source_separation_performed"] is False
    assert payload["stems_generated"] is False


def test_smoke_tests_do_not_separate_or_download(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(check_source_separation_setup, "EXAMPLE_CONFIG", tmp_path / "missing.example.json")
    monkeypatch.setattr(check_source_separation_setup, "LOCAL_CONFIG", tmp_path / "missing.local.json")
    payload = run_source_separation_smoke_tests.run_source_separation_smoke_tests()
    assert payload["smoke_test_passed"] is False
    assert payload["source_separation_performed"] is False
    assert payload["stems_generated"] is False
    assert payload["generated_stem_paths"] == []
    assert payload["downloads_performed"] is False
    assert payload["model_training_has_occurred"] is False
    assert payload["witness_policy"] == "weak_evidence_not_truth"
    assert payload["no_fake_stems"] is True


def test_planner_does_not_generate_stems_or_train() -> None:
    payload = plan_source_separation_witness.build_source_separation_witness_plan()
    assert payload["status"] == "planned"
    assert payload["source_separation_performed"] is False
    assert payload["stems_generated"] is False
    assert payload["audio_processing_performed"] is False
    assert payload["downloads_performed"] is False
    assert payload["model_training_has_occurred"] is False
    assert payload["witness_policy"] == "weak_evidence_not_truth"
    assert payload["training_use_allowed"] == "false_by_default"


def test_source_separation_outputs_not_ground_truth() -> None:
    decision = model_usage_policy("demucs")
    assert decision.allowed is True
    assert "weak_evidence" in decision.tags


def test_reports_are_path_safe(tmp_path: Path) -> None:
    json_path, md_path, _ = check_source_separation_setup.write_source_separation_setup_report(
        tmp_path / "reports" / "model_integrations"
    )
    plan_json, plan_md, _ = plan_source_separation_witness.write_plan_report(tmp_path / "reports" / "source_separation")
    assert ("C:/" + "Users/") not in json_path.read_text(encoding="utf-8")
    assert ("C:\\" + "Users\\") not in md_path.read_text(encoding="utf-8")
    assert ("C:/" + "Users/") not in plan_json.read_text(encoding="utf-8")
    assert ("C:\\" + "Users\\") not in plan_md.read_text(encoding="utf-8")
