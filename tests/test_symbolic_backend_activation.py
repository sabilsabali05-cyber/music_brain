from __future__ import annotations

import json
from pathlib import Path

from scripts import (
    bootstrap_symbolic_model_local_config,
    check_symbolic_backend_activation,
    run_moonbeam_smoke_test,
)


def test_local_config_file_is_ignored() -> None:
    gitignore_text = Path(".gitignore").read_text(encoding="utf-8")
    assert "config/model_integrations/model_integrations.local.json" in gitignore_text


def test_bootstrap_redacts_private_paths(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(bootstrap_symbolic_model_local_config, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(
        bootstrap_symbolic_model_local_config,
        "CONFIG_DIR",
        tmp_path / "config" / "model_integrations",
    )
    monkeypatch.setattr(
        bootstrap_symbolic_model_local_config,
        "EXAMPLE_CONFIG",
        tmp_path / "config" / "model_integrations" / "model_integrations.example.json",
    )
    monkeypatch.setattr(
        bootstrap_symbolic_model_local_config,
        "LOCAL_CONFIG",
        tmp_path / "config" / "model_integrations" / "model_integrations.local.json",
    )
    payload = bootstrap_symbolic_model_local_config.bootstrap_local_config()
    assert payload["private_paths_redacted"] is True
    text = json.dumps(payload, ensure_ascii=True)
    assert ("C:/" + "Users/") not in text
    assert ("C:\\" + "Users\\") not in text


def test_disabled_does_not_fake_availability(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(run_moonbeam_smoke_test, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(
        run_moonbeam_smoke_test,
        "LOCAL_CONFIG",
        tmp_path / "config" / "model_integrations" / "model_integrations.local.json",
    )
    monkeypatch.setattr(
        run_moonbeam_smoke_test,
        "EXAMPLE_CONFIG",
        tmp_path / "config" / "model_integrations" / "model_integrations.example.json",
    )
    payload = run_moonbeam_smoke_test.run_moonbeam_smoke_test()
    assert payload["status"] == "disabled"
    assert payload["moonbeam_available"] is False
    assert payload["real_smoke_passed"] is False


def test_missing_paths_does_not_fake_availability(monkeypatch, tmp_path: Path) -> None:
    cfg_path = tmp_path / "config" / "model_integrations" / "model_integrations.local.json"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(
        json.dumps(
            {
                "models": {
                    "moonbeam": {
                        "enabled": True,
                        "repo_path": "missing_repo",
                        "model_path": "missing_model",
                        "tokenizer_path": "missing_tok",
                    }
                }
            },
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(run_moonbeam_smoke_test, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(run_moonbeam_smoke_test, "LOCAL_CONFIG", cfg_path)
    monkeypatch.setattr(run_moonbeam_smoke_test, "EXAMPLE_CONFIG", tmp_path / "missing.example.json")
    payload = run_moonbeam_smoke_test.run_moonbeam_smoke_test()
    assert payload["status"] == "unavailable"
    assert payload["unavailable_reason"] == "missing_paths"
    assert payload["moonbeam_available"] is False


def test_available_requires_real_smoke_artifact(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config" / "model_integrations" / "model_integrations.local.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps({"models": {"moonbeam": {"enabled": True}}}, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    smoke_path = tmp_path / "reports" / "model_integrations" / "moonbeam_smoke_result.json"
    smoke_path.parent.mkdir(parents=True, exist_ok=True)
    smoke_path.write_text(
        json.dumps({"status": "available", "real_smoke_passed": True}, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(check_symbolic_backend_activation, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(check_symbolic_backend_activation, "CONFIG_PATH", config_path)
    monkeypatch.setattr(
        check_symbolic_backend_activation,
        "SMOKE_REPORT_FILES",
        {
            "moonbeam": smoke_path,
            "musicbert": tmp_path / "reports/model_integrations/musicbert_smoke_result.json",
            "midigpt": tmp_path / "reports/model_integrations/midigpt_smoke_result.json",
            "text2midi": tmp_path / "reports/model_integrations/text2midi_smoke_result.json",
        },
    )
    payload = check_symbolic_backend_activation.evaluate_activation_status()
    assert payload["moonbeam_available"] is True
    assert payload["moonbeam_smoke_passed"] is True
    assert payload["model_training_has_occurred"] is False
    assert payload["trained_model_generation_allowed"] is False
    assert payload["cloud_symbolic_available"] is False


def test_model_weight_dirs_are_ignored() -> None:
    gitignore_text = Path(".gitignore").read_text(encoding="utf-8")
    assert "external_models/" in gitignore_text
    assert "model_weights/" in gitignore_text
