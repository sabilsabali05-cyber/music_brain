from __future__ import annotations

import json
from pathlib import Path

from features.symbolic_ir import SymbolicGenerationRequest, SymbolicPromptSpec
from features.symbolic_model_ensemble.backends.midigpt_adapter import MidiGptAdapter
from features.symbolic_model_ensemble.ensemble_orchestrator import SymbolicEnsembleOrchestrator
from scripts import check_midigpt_setup, generate_midigpt_variation_scaffold, run_midigpt_smoke_test


def _write_model_integrations_config(path: Path, midigpt: dict) -> None:
    payload = {"config_version": 1, "models": {"midigpt": midigpt}}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _request(task_type: str = "drum_variation") -> SymbolicGenerationRequest:
    return SymbolicGenerationRequest(
        request_id="midigpt_req_1",
        prompt_spec=SymbolicPromptSpec(
            prompt_text="test prompt",
            duration_seconds=32.0,
            tempo=120.0,
            meter="4/4",
            key_hint="unknown",
            ratio_plan="golden_ratio",
            section_labels=["a", "b"],
            requested_track_roles=["drums", "bass"],
        ),
        task_type=task_type,
        source_backend="midigpt",
        conditioning={},
    )


def test_midigpt_disabled_by_default(monkeypatch, tmp_path: Path) -> None:
    example_path = tmp_path / "config" / "model_integrations" / "model_integrations.example.json"
    _write_model_integrations_config(
        example_path,
        {
            "enabled": False,
            "repo_path": "<PATH_TO_REPO>",
            "model_path": "<PATH_TO_MODEL>",
            "tokenizer_path": "<PATH_TO_MODEL>",
            "device": "<DEVICE>",
            "smoke_test_enabled": False,
        },
    )
    monkeypatch.setattr(check_midigpt_setup, "EXAMPLE_CONFIG", example_path)
    monkeypatch.setattr(check_midigpt_setup, "LOCAL_CONFIG", tmp_path / "missing.local.json")
    payload = check_midigpt_setup.evaluate_midigpt_setup()
    assert payload["midigpt_configured"] is False
    assert payload["midigpt_available"] is False
    assert payload["unavailable_reason"] == "disabled_or_missing_local_config"


def test_missing_local_config_safe(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(check_midigpt_setup, "EXAMPLE_CONFIG", tmp_path / "missing.example.json")
    monkeypatch.setattr(check_midigpt_setup, "LOCAL_CONFIG", tmp_path / "missing.local.json")
    payload = check_midigpt_setup.evaluate_midigpt_setup()
    assert payload["midigpt_configured"] is False
    assert payload["midigpt_available"] is False
    assert payload["smoke_test_passed"] is False
    assert payload["unavailable_reason"] == "disabled_or_missing_local_config"


def test_missing_model_path_unavailable(monkeypatch, tmp_path: Path) -> None:
    local_config = tmp_path / "config" / "model_integrations" / "model_integrations.local.json"
    repo_dir = tmp_path / "midigpt_repo"
    tokenizer = tmp_path / "tok.model"
    repo_dir.mkdir(parents=True, exist_ok=True)
    tokenizer.write_text("x", encoding="utf-8")
    _write_model_integrations_config(
        local_config,
        {
            "enabled": True,
            "repo_path": repo_dir.as_posix(),
            "model_path": (tmp_path / "missing_model.bin").as_posix(),
            "tokenizer_path": tokenizer.as_posix(),
            "device": "cpu",
            "smoke_test_enabled": True,
        },
    )
    monkeypatch.setattr(check_midigpt_setup, "LOCAL_CONFIG", local_config)
    monkeypatch.setattr(check_midigpt_setup, "EXAMPLE_CONFIG", tmp_path / "missing.example.json")
    payload = check_midigpt_setup.evaluate_midigpt_setup()
    assert payload["midigpt_configured"] is False
    assert payload["unavailable_reason"] == "model_path_missing"


def test_adapter_never_fakes_generation() -> None:
    adapter = MidiGptAdapter()
    result = adapter.generate_variation(_request())
    assert result.status == "unavailable"
    assert result.details["backend"] == "midigpt"
    assert result.details["no_fake_generation"] is True


def test_variation_methods_explicit_unavailable() -> None:
    adapter = MidiGptAdapter()
    request = _request()
    rows = [
        adapter.generate_drum_variation(request),
        adapter.generate_groove_variation(request),
        adapter.generate_density_variation(request),
        adapter.multitrack_infill(request),
        adapter.bar_level_infill(request),
        adapter.track_level_infill(request),
    ]
    for row in rows:
        assert row.status == "unavailable"
        assert row.details["reason"]
        assert row.details["no_fake_generation"] is True


def test_smoke_test_no_download_or_training(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(check_midigpt_setup, "LOCAL_CONFIG", tmp_path / "missing.local.json")
    monkeypatch.setattr(check_midigpt_setup, "EXAMPLE_CONFIG", tmp_path / "missing.example.json")
    payload = run_midigpt_smoke_test.run_midigpt_smoke_test()
    assert payload["status"] == "unavailable"
    assert payload["unavailable_reason"] == "disabled_or_missing_local_config"
    assert payload["model_training_has_occurred"] is False
    notes = " ".join(payload["smoke_test_notes"]).lower()
    assert "no weights downloaded" in notes
    assert "no training" in notes


def test_public_reports_have_no_user_paths(tmp_path: Path) -> None:
    json_path, md_path, _ = check_midigpt_setup.write_midigpt_setup_report(tmp_path / "reports" / "model_integrations")
    assert ("C:/" + "Users/") not in json_path.read_text(encoding="utf-8")
    assert ("C:\\" + "Users\\") not in md_path.read_text(encoding="utf-8")


def test_routing_prefers_midigpt_variation_tasks() -> None:
    plan = SymbolicEnsembleOrchestrator.symbolic_routing_plan()
    assert "drums" in plan["midigpt_preferred_for"]
    assert "groove" in plan["midigpt_preferred_for"]
    assert "density variation" in plan["midigpt_preferred_for"]
    assert "multitrack infill" in plan["midigpt_preferred_for"]


def test_model_training_has_occurred_false() -> None:
    payload = check_midigpt_setup.evaluate_midigpt_setup()
    assert payload["model_training_has_occurred"] is False


def test_variation_scaffold_does_not_fake_midi_outputs(tmp_path: Path) -> None:
    out_dir = tmp_path / "reports" / "symbolic_backends"
    src_dir = tmp_path / "outputs" / "symbolic_ensemble_v1" / "generated_candidates"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "cand_1.ir.json").write_text("{}", encoding="utf-8")
    json_path, _, payload = generate_midigpt_variation_scaffold.write_variation_report(
        out_dir, tmp_path / "outputs" / "symbolic_ensemble_v1"
    )
    assert payload["no_fake_generation"] is True
    assert payload["variations_generated"] is False
    assert payload["generated_midi_outputs"] == []
    text = json_path.read_text(encoding="utf-8")
    assert ("C:/" + "Users/") not in text
    assert ("C:\\" + "Users\\") not in text
