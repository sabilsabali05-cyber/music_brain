from __future__ import annotations

import json
from pathlib import Path

from features.symbolic_ir import SymbolicGenerationRequest, SymbolicPromptSpec
from features.symbolic_model_ensemble.backends.text2midi_adapter import Text2MidiAdapter
from features.symbolic_model_ensemble.ensemble_orchestrator import SymbolicEnsembleOrchestrator
from scripts import check_text2midi_setup, generate_text2midi_prompt_sketch_scaffold, run_text2midi_smoke_test


def _write_model_integrations_config(path: Path, text2midi: dict) -> None:
    payload = {"config_version": 1, "models": {"text2midi": text2midi}}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _request() -> SymbolicGenerationRequest:
    return SymbolicGenerationRequest(
        request_id="text2midi_req_1",
        prompt_spec=SymbolicPromptSpec(
            prompt_text="neo soul pocket with bright chord stabs",
            duration_seconds=24.0,
            tempo=96.0,
            meter="4/4",
            key_hint="A minor",
            ratio_plan="golden_ratio",
            section_labels=["a", "b"],
            requested_track_roles=["chords", "bass"],
        ),
        task_type="prompt_sketch",
        source_backend="text2midi",
        conditioning={},
    )


def test_text2midi_disabled_by_default(monkeypatch, tmp_path: Path) -> None:
    example_path = tmp_path / "config" / "model_integrations" / "model_integrations.example.json"
    _write_model_integrations_config(
        example_path,
        {
            "enabled": False,
            "repo_path": "<PATH_TO_REPO>",
            "model_path": "<PATH_TO_MODEL>",
            "device": "<DEVICE>",
            "smoke_test_enabled": False,
        },
    )
    monkeypatch.setattr(check_text2midi_setup, "EXAMPLE_CONFIG", example_path)
    monkeypatch.setattr(check_text2midi_setup, "LOCAL_CONFIG", tmp_path / "missing.local.json")
    payload = check_text2midi_setup.evaluate_text2midi_setup()
    assert payload["text2midi_configured"] is False
    assert payload["text2midi_available"] is False
    assert payload["unavailable_reason"] == "disabled_or_missing_local_config"


def test_missing_local_config_safe(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(check_text2midi_setup, "EXAMPLE_CONFIG", tmp_path / "missing.example.json")
    monkeypatch.setattr(check_text2midi_setup, "LOCAL_CONFIG", tmp_path / "missing.local.json")
    payload = check_text2midi_setup.evaluate_text2midi_setup()
    assert payload["text2midi_configured"] is False
    assert payload["text2midi_available"] is False
    assert payload["smoke_test_passed"] is False
    assert payload["unavailable_reason"] == "disabled_or_missing_local_config"


def test_missing_model_path_unavailable(monkeypatch, tmp_path: Path) -> None:
    local_config = tmp_path / "config" / "model_integrations" / "model_integrations.local.json"
    repo_dir = tmp_path / "text2midi_repo"
    repo_dir.mkdir(parents=True, exist_ok=True)
    _write_model_integrations_config(
        local_config,
        {
            "enabled": True,
            "repo_path": repo_dir.as_posix(),
            "model_path": (tmp_path / "missing_model.bin").as_posix(),
            "device": "cpu",
            "smoke_test_enabled": True,
        },
    )
    monkeypatch.setattr(check_text2midi_setup, "LOCAL_CONFIG", local_config)
    monkeypatch.setattr(check_text2midi_setup, "EXAMPLE_CONFIG", tmp_path / "missing.example.json")
    payload = check_text2midi_setup.evaluate_text2midi_setup()
    assert payload["text2midi_configured"] is False
    assert payload["unavailable_reason"] == "model_path_missing"


def test_adapter_never_fakes_generation() -> None:
    adapter = Text2MidiAdapter()
    result = adapter.generate(_request())
    assert result.status == "unavailable"
    assert result.details["backend"] == "text2midi"
    assert result.details["no_fake_generation"] is True
    assert result.details["scores_generated"] is False


def test_smoke_test_no_download_or_training(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(check_text2midi_setup, "LOCAL_CONFIG", tmp_path / "missing.local.json")
    monkeypatch.setattr(check_text2midi_setup, "EXAMPLE_CONFIG", tmp_path / "missing.example.json")
    payload = run_text2midi_smoke_test.run_text2midi_smoke_test()
    assert payload["status"] == "unavailable"
    assert payload["unavailable_reason"] == "disabled_or_missing_local_config"
    assert payload["model_training_has_occurred"] is False
    notes = " ".join(payload["smoke_test_notes"]).lower()
    assert "no weights downloaded" in notes
    assert "no training" in notes


def test_public_reports_have_no_user_paths(tmp_path: Path) -> None:
    json_path, md_path, _ = check_text2midi_setup.write_text2midi_setup_report(tmp_path / "reports" / "model_integrations")
    assert ("C:/" + "Users/") not in json_path.read_text(encoding="utf-8")
    assert ("C:\\" + "Users\\") not in md_path.read_text(encoding="utf-8")


def test_routing_explicit_text2midi_role() -> None:
    plan = SymbolicEnsembleOrchestrator.symbolic_routing_plan()
    assert "prompt sketch" in plan["text2midi_preferred_for"]
    assert "text-conditioned seed" in plan["text2midi_preferred_for"]
    assert "chord/key/tempo prompt conditioning" in plan["text2midi_preferred_for"]
    assert "user vocabulary future target" in plan["text2midi_preferred_for"]


def test_prompt_sketch_scaffold_default_unavailable_safe(tmp_path: Path) -> None:
    out_dir = tmp_path / "reports" / "symbolic_backends"
    src_dir = tmp_path / "outputs" / "symbolic_ensemble_v1" / "generated_candidates"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "cand_1.ir.json").write_text("{}", encoding="utf-8")
    json_path, _, payload = generate_text2midi_prompt_sketch_scaffold.write_prompt_sketch_report(
        out_dir, tmp_path / "outputs" / "symbolic_ensemble_v1"
    )
    assert payload["no_fake_generation"] is True
    assert payload["sketches_generated"] is False
    assert payload["scores_generated"] is False
    text = json_path.read_text(encoding="utf-8")
    assert ("C:/" + "Users/") not in text
    assert ("C:\\" + "Users\\") not in text
