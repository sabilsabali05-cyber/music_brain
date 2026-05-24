from __future__ import annotations

import json
from pathlib import Path

from features.symbolic_model_ensemble.backends.musicbert_adapter import MusicBertAdapter
from features.symbolic_model_ensemble.ensemble_orchestrator import SymbolicEnsembleOrchestrator
from scripts import check_musicbert_setup, evaluate_symbolic_candidates_musicbert, run_musicbert_smoke_test


def _write_model_integrations_config(path: Path, musicbert: dict) -> None:
    payload = {"config_version": 1, "models": {"musicbert": musicbert}}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def test_musicbert_disabled_by_default(monkeypatch, tmp_path: Path) -> None:
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
            "embedding_dim": 768,
            "output_dir": "<PATH_TO_REPO>",
        },
    )
    monkeypatch.setattr(check_musicbert_setup, "EXAMPLE_CONFIG", example_path)
    monkeypatch.setattr(check_musicbert_setup, "LOCAL_CONFIG", tmp_path / "missing.local.json")
    payload = check_musicbert_setup.evaluate_musicbert_setup()
    assert payload["musicbert_configured"] is False
    assert payload["musicbert_available"] is False
    assert payload["unavailable_reason"] == "disabled_or_missing_local_config"


def test_missing_local_config_is_safe(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(check_musicbert_setup, "EXAMPLE_CONFIG", tmp_path / "missing.example.json")
    monkeypatch.setattr(check_musicbert_setup, "LOCAL_CONFIG", tmp_path / "missing.local.json")
    payload = check_musicbert_setup.evaluate_musicbert_setup()
    assert payload["musicbert_configured"] is False
    assert payload["musicbert_available"] is False
    assert payload["smoke_test_passed"] is False
    assert payload["unavailable_reason"] == "disabled_or_missing_local_config"


def test_missing_model_path_returns_unavailable(monkeypatch, tmp_path: Path) -> None:
    local_config = tmp_path / "config" / "model_integrations" / "model_integrations.local.json"
    repo_dir = tmp_path / "musicbert_repo"
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
            "embedding_dim": 768,
            "output_dir": repo_dir.as_posix(),
        },
    )
    monkeypatch.setattr(check_musicbert_setup, "LOCAL_CONFIG", local_config)
    monkeypatch.setattr(check_musicbert_setup, "EXAMPLE_CONFIG", tmp_path / "missing.example.json")
    payload = check_musicbert_setup.evaluate_musicbert_setup()
    assert payload["musicbert_configured"] is False
    assert payload["unavailable_reason"] == "model_path_missing"


def test_adapter_never_fakes_evaluation() -> None:
    adapter = MusicBertAdapter()
    result = adapter.evaluate(None)
    assert result.status == "unavailable"
    assert result.details["backend"] == "musicbert"
    assert result.details["no_fake_evaluation"] is True


def test_rank_and_evaluate_return_explicit_unavailable_state() -> None:
    adapter = MusicBertAdapter()
    eval_result = adapter.evaluate(None)
    rank_result = adapter.rank([])
    assert eval_result.status == "unavailable"
    assert rank_result.status == "unavailable"
    assert eval_result.details["reason"]
    assert rank_result.details["reason"]


def test_smoke_test_does_not_download_or_train(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(check_musicbert_setup, "LOCAL_CONFIG", tmp_path / "missing.local.json")
    monkeypatch.setattr(check_musicbert_setup, "EXAMPLE_CONFIG", tmp_path / "missing.example.json")
    payload = run_musicbert_smoke_test.run_musicbert_smoke_test()
    assert payload["status"] == "disabled"
    assert payload["unavailable_reason"] == "disabled"
    assert payload["model_training_has_occurred"] is False
    assert payload["real_smoke_passed"] is False


def test_public_musicbert_reports_contain_no_private_paths(tmp_path: Path) -> None:
    json_path, md_path, _ = check_musicbert_setup.write_musicbert_setup_report(tmp_path / "reports" / "model_integrations")
    assert ("C:/" + "Users/") not in json_path.read_text(encoding="utf-8")
    assert ("C:\\" + "Users\\") not in md_path.read_text(encoding="utf-8")


def test_musicbert_preferred_symbolic_ranking_backend() -> None:
    plan = SymbolicEnsembleOrchestrator.symbolic_routing_plan()
    assert "ranking" in plan["musicbert_preferred_for"]
    assert "evaluation" in plan["musicbert_preferred_for"]
    assert "symbolic similarity" in plan["musicbert_preferred_for"]
    assert "accompaniment fit" in plan["musicbert_preferred_for"]
    assert "melody fit" in plan["musicbert_preferred_for"]
    assert "taste-ranker future target" in plan["musicbert_preferred_for"]


def test_model_training_has_occurred_remains_false() -> None:
    payload = check_musicbert_setup.evaluate_musicbert_setup()
    assert payload["model_training_has_occurred"] is False


def test_candidate_evaluation_report_does_not_fake_scores(tmp_path: Path) -> None:
    out_dir = tmp_path / "reports" / "symbolic_backends"
    src_dir = tmp_path / "outputs" / "symbolic_ensemble_v1" / "generated_candidates"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "cand_1.ir.json").write_text("{}", encoding="utf-8")
    json_path, _, payload = evaluate_symbolic_candidates_musicbert.write_evaluation_report(
        out_dir, tmp_path / "outputs" / "symbolic_ensemble_v1"
    )
    assert payload["no_fake_evaluation"] is True
    assert payload["scores_generated"] is False
    assert payload["candidate_count"] == 1
    text = json_path.read_text(encoding="utf-8")
    assert ("C:/" + "Users/") not in text
    assert ("C:\\" + "Users\\") not in text
