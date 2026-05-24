from __future__ import annotations

import json
from pathlib import Path

from features.symbolic_ir import SymbolicBackendCapability
from features.symbolic_model_ensemble.backends.moonbeam_adapter import MoonbeamAdapter
from features.symbolic_model_ensemble.ensemble_orchestrator import SymbolicEnsembleOrchestrator
from scripts import check_moonbeam_setup, run_moonbeam_smoke_test


def _write_model_integrations_config(path: Path, moonbeam: dict) -> None:
    payload = {
        "config_version": 1,
        "models": {
            "moonbeam": moonbeam,
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def test_moonbeam_disabled_by_default(monkeypatch, tmp_path: Path) -> None:
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
            "max_tokens": 512,
            "output_dir": "<PATH_TO_REPO>",
        },
    )
    monkeypatch.setattr(check_moonbeam_setup, "EXAMPLE_CONFIG", example_path)
    monkeypatch.setattr(check_moonbeam_setup, "LOCAL_CONFIG", tmp_path / "missing.local.json")
    payload = check_moonbeam_setup.evaluate_moonbeam_setup()
    assert payload["moonbeam_configured"] is False
    assert payload["moonbeam_available"] is False
    assert payload["unavailable_reason"] == "disabled_or_missing_local_config"


def test_missing_local_config_is_safe(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(check_moonbeam_setup, "EXAMPLE_CONFIG", tmp_path / "missing.example.json")
    monkeypatch.setattr(check_moonbeam_setup, "LOCAL_CONFIG", tmp_path / "missing.local.json")
    payload = check_moonbeam_setup.evaluate_moonbeam_setup()
    assert payload["moonbeam_configured"] is False
    assert payload["moonbeam_available"] is False
    assert payload["smoke_test_passed"] is False
    assert payload["unavailable_reason"] == "disabled_or_missing_local_config"


def test_missing_model_path_returns_unavailable(monkeypatch, tmp_path: Path) -> None:
    local_config = tmp_path / "config" / "model_integrations" / "model_integrations.local.json"
    repo_dir = tmp_path / "moonbeam_repo"
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
            "max_tokens": 512,
            "output_dir": repo_dir.as_posix(),
        },
    )
    monkeypatch.setattr(check_moonbeam_setup, "LOCAL_CONFIG", local_config)
    monkeypatch.setattr(check_moonbeam_setup, "EXAMPLE_CONFIG", tmp_path / "missing.example.json")
    payload = check_moonbeam_setup.evaluate_moonbeam_setup()
    assert payload["moonbeam_configured"] is False
    assert payload["unavailable_reason"] == "model_path_missing"


def test_adapter_never_fakes_generation_when_unavailable() -> None:
    adapter = MoonbeamAdapter()
    result = adapter.generate(None)  # type: ignore[arg-type]
    assert result.status == "unavailable"
    assert result.details["backend"] == "moonbeam"
    assert result.details["no_fake_generation"] is True


def test_smoke_test_does_not_download_or_train(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(check_moonbeam_setup, "LOCAL_CONFIG", tmp_path / "missing.local.json")
    monkeypatch.setattr(check_moonbeam_setup, "EXAMPLE_CONFIG", tmp_path / "missing.example.json")
    payload = run_moonbeam_smoke_test.run_moonbeam_smoke_test()
    assert payload["status"] == "disabled"
    assert payload["unavailable_reason"] == "disabled"
    assert payload["model_training_has_occurred"] is False
    assert payload["real_smoke_passed"] is False


def test_public_moonbeam_reports_contain_no_private_paths(tmp_path: Path) -> None:
    json_path, md_path, _ = check_moonbeam_setup.write_moonbeam_setup_report(tmp_path / "reports" / "model_integrations")
    assert ("C:/" + "Users/") not in json_path.read_text(encoding="utf-8")
    assert ("C:\\" + "Users\\") not in md_path.read_text(encoding="utf-8")


def test_moonbeam_preferred_symbolic_continuation_backend(monkeypatch, tmp_path: Path) -> None:
    orchestrator = SymbolicEnsembleOrchestrator()

    class FakeMoonbeam:
        backend_id = "moonbeam"

        def check_available(self):
            return SymbolicBackendCapability(
                backend_id="moonbeam",
                backend_role="main",
                supported_operations=["continuation"],
                status="available",
                reason="ok",
            )

        describe_capabilities = check_available

        def continue_ir(self, request):
            return type("Res", (), {"status": "ok", "reason": "ok", "candidate": _fake_candidate("moonbeam", 10)})()

        def generate(self, request):
            return type("Res", (), {"status": "unavailable", "reason": "n/a", "candidate": None})()

        infill_ir = generate
        evaluate = generate
        rank = generate

        def explain_result(self, result):
            return "ok"

    class FakeUnavailable:
        def __init__(self, backend_id: str):
            self.backend_id = backend_id

        def check_available(self):
            return SymbolicBackendCapability(
                backend_id=self.backend_id,
                backend_role="none",
                supported_operations=[],
                status="unavailable",
                reason="disabled",
            )

        describe_capabilities = check_available

        def generate(self, request):
            return type("Res", (), {"status": "unavailable", "reason": "disabled", "candidate": None})()

        continue_ir = generate
        infill_ir = generate
        evaluate = generate
        rank = generate

        def explain_result(self, result):
            return "disabled"

    orchestrator.registry["moonbeam"] = FakeMoonbeam()
    orchestrator.registry["text2midi"] = FakeUnavailable("text2midi")
    orchestrator.registry["midigpt"] = FakeUnavailable("midigpt")
    orchestrator.registry["musicbert"] = FakeUnavailable("musicbert")
    orchestrator.registry["example_retrieval"] = FakeUnavailable("example_retrieval")
    payload = orchestrator.generate("moonbeam route", output_root=tmp_path / "out")
    assert payload["selected_candidate_backend"] == "moonbeam"


def test_fallback_remains_explicit_when_moonbeam_unavailable(tmp_path: Path) -> None:
    orchestrator = SymbolicEnsembleOrchestrator()
    payload = orchestrator.generate("fallback route", output_root=tmp_path / "out")
    assert payload["example_retrieval_fallback"] is True
    assert payload["no_real_symbolic_backend_available"] is True
    assert payload["not_model_trained_on_user_data"] is True


def test_model_training_has_occurred_remains_false() -> None:
    payload = check_moonbeam_setup.evaluate_moonbeam_setup()
    assert payload["model_training_has_occurred"] is False


def _fake_candidate(backend_id: str, note_count: int):
    from features.symbolic_ir import (
        SymbolicGenerationCandidate,
        SymbolicModelProvenance,
        SymbolicMusicIR,
        SymbolicNoteEvent,
        SymbolicSection,
        SymbolicTrack,
    )

    notes = [SymbolicNoteEvent(start_tick=i * 120, duration_tick=120, pitch=60 + (i % 5), velocity=82, channel=0) for i in range(note_count)]
    ir = SymbolicMusicIR(
        composition_id=f"{backend_id}_comp",
        prompt_text="prompt",
        duration_seconds=16.0,
        tempo=120.0,
        meter="4/4",
        key_hint="unknown",
        ratio_plan="golden_ratio",
        section_labels=["main"],
        sections=[SymbolicSection(section_label="main", start_tick=0, end_tick=960)],
        tracks=[SymbolicTrack(track_id="t1", track_role="lead", instrument_hint="piano", note_events=notes)],
        source_backend=backend_id,
        generation_method="test",
    )
    return SymbolicGenerationCandidate(
        candidate_id=f"{backend_id}_cand",
        ir=ir,
        source_backend=backend_id,
        generation_method="test",
        model_provenance=SymbolicModelProvenance(source_backend=backend_id, generation_method="test"),
    )
