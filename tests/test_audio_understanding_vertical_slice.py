from __future__ import annotations

import json
from pathlib import Path

from features.audio_understanding.essentia_adapter import EssentiaAdapter
from features.audio_understanding.mert_adapter import MERTAdapter
from features.audio_understanding.muq_adapter import MuQAdapter
from scripts import check_audio_understanding_setup, plan_audio_texture_embedding, run_audio_understanding_smoke_tests


def _write_minimal_example_config(path: Path) -> None:
    payload = {
        "config_version": 1,
        "models": {
            "essentia": {
                "enabled": False,
                "package_required": "essentia",
                "device": "<DEVICE>",
                "smoke_test_enabled": False,
                "output_dir": "<PATH_TO_REPO>",
            },
            "muq": {
                "enabled": False,
                "repo_path": "<PATH_TO_REPO>",
                "model_path": "<PATH_TO_MODEL>",
                "tokenizer_path": "<PATH_TO_MODEL>",
                "device": "<DEVICE>",
                "smoke_test_enabled": False,
                "embedding_dim": 1024,
                "output_dir": "<PATH_TO_REPO>",
            },
            "mert": {
                "enabled": False,
                "repo_path": "<PATH_TO_REPO>",
                "model_path": "<PATH_TO_MODEL>",
                "tokenizer_path": "<PATH_TO_MODEL>",
                "device": "<DEVICE>",
                "smoke_test_enabled": False,
                "embedding_dim": 768,
                "output_dir": "<PATH_TO_REPO>",
            },
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def test_models_disabled_and_unavailable_by_default(monkeypatch, tmp_path: Path) -> None:
    example_path = tmp_path / "config" / "model_integrations" / "model_integrations.example.json"
    _write_minimal_example_config(example_path)

    for adapter_cls in (EssentiaAdapter, MuQAdapter, MERTAdapter):
        adapter = adapter_cls()
        monkeypatch.setattr(adapter, "_config_paths", lambda: (tmp_path / "missing.local.json", example_path))
        availability = adapter.availability()
        assert availability["configured"] is False
        assert availability["available"] is False


def test_setup_checker_performs_no_audio_processing(monkeypatch, tmp_path: Path) -> None:
    example_path = tmp_path / "config" / "model_integrations" / "model_integrations.example.json"
    _write_minimal_example_config(example_path)
    monkeypatch.setattr(check_audio_understanding_setup.EssentiaAdapter, "_config_paths", lambda _: (tmp_path / "missing.local.json", example_path))
    monkeypatch.setattr(check_audio_understanding_setup.MuQAdapter, "_config_paths", lambda _: (tmp_path / "missing.local.json", example_path))
    monkeypatch.setattr(check_audio_understanding_setup.MERTAdapter, "_config_paths", lambda _: (tmp_path / "missing.local.json", example_path))
    payload = check_audio_understanding_setup.evaluate_audio_understanding_setup()
    assert payload["audio_processing_performed"] is False
    assert payload["embeddings_generated"] is False
    assert payload["model_training_has_occurred"] is False
    assert payload["downloads_performed"] is False
    assert payload["smoke_tests_passed"] is False


def test_smoke_test_runner_stays_unavailable_safe(monkeypatch, tmp_path: Path) -> None:
    example_path = tmp_path / "config" / "model_integrations" / "model_integrations.example.json"
    _write_minimal_example_config(example_path)
    monkeypatch.setattr(check_audio_understanding_setup.EssentiaAdapter, "_config_paths", lambda _: (tmp_path / "missing.local.json", example_path))
    monkeypatch.setattr(check_audio_understanding_setup.MuQAdapter, "_config_paths", lambda _: (tmp_path / "missing.local.json", example_path))
    monkeypatch.setattr(check_audio_understanding_setup.MERTAdapter, "_config_paths", lambda _: (tmp_path / "missing.local.json", example_path))
    payload = run_audio_understanding_smoke_tests.run_audio_understanding_smoke_tests()
    assert payload["status"] == "unavailable"
    assert payload["smoke_tests_passed"] is False
    assert payload["model_training_has_occurred"] is False
    assert payload["audio_processing_performed"] is False
    assert payload["embeddings_generated"] is False


def test_texture_embedding_plan_is_plan_only(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(plan_audio_texture_embedding, "ROOT_DIR", tmp_path)
    payload = plan_audio_texture_embedding.build_audio_texture_embedding_plan()
    assert payload["status"] == "planned"
    assert payload["audio_processing_performed"] is False
    assert payload["embeddings_generated"] is False
    assert payload["model_training_has_occurred"] is False
    assert payload["downloads_performed"] is False
    assert "splice_production_only" in payload["training_exclusions"]["preserved_policies"]
    assert "production_only_training_excluded" in payload["training_exclusions"]["preserved_policies"]


def test_planner_reports_are_public_path_safe(tmp_path: Path) -> None:
    json_path, md_path, _ = plan_audio_texture_embedding.write_plan_report(tmp_path / "reports" / "audio_understanding")
    json_text = json_path.read_text(encoding="utf-8")
    md_text = md_path.read_text(encoding="utf-8")
    assert ("C:/" + "Users/") not in json_text
    assert ("C:\\" + "Users\\") not in json_text
    assert ("C:/" + "Users/") not in md_text
    assert ("C:\\" + "Users\\") not in md_text
