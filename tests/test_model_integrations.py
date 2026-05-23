from __future__ import annotations

import json
from pathlib import Path

from features.model_integrations.model_policy import model_usage_policy, training_source_policy
from features.model_integrations.model_registry import list_model_families, list_model_integrations
from scripts import check_model_integrations as checker


def _write_config(path: Path, enabled_overrides: dict[str, bool] | None = None) -> None:
    models = {}
    for record in list_model_integrations():
        enabled = bool((enabled_overrides or {}).get(record.model_id, False))
        models[record.model_id] = {
            "enabled": enabled,
            "model_path": "<PATH_TO_MODEL>",
            "repo_path": "<PATH_TO_REPO>",
            "device": "<DEVICE>",
        }
    payload = {"config_version": 1, "models": models}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def test_all_requested_model_families_exist() -> None:
    families = list_model_families()
    assert families == {
        "symbolic_generation": ["moonbeam", "midigpt", "text2midi"],
        "symbolic_understanding": ["musicbert"],
        "transcription": ["yourmt3", "basic_pitch"],
        "audio_understanding": ["muq", "mert", "essentia"],
        "audio_text_retrieval": ["clap", "mulan_style"],
        "source_separation": ["demucs"],
        "audio_generation_reference": ["musicgen", "audiocraft", "musicgen_stem"],
        "texture_and_sound_selection": ["texture_embedding_model", "synplant_seed_selector", "synplant_patch_ranker"],
        "daw_agent_tools": ["ableton_exporter", "max_for_live_bridge", "puredata_plugdata_bridge"],
    }


def test_all_models_default_to_disabled_unavailable(monkeypatch, tmp_path: Path) -> None:
    example_path = tmp_path / "config" / "model_integrations" / "model_integrations.example.json"
    _write_config(example_path)
    local_path = tmp_path / "config" / "model_integrations" / "model_integrations.local.json"
    monkeypatch.setattr(checker, "EXAMPLE_CONFIG_PATH", example_path)
    monkeypatch.setattr(checker, "LOCAL_CONFIG_PATH", local_path)

    payload = checker.evaluate_model_integrations()
    assert payload["using_local_config"] is False
    assert payload["configured_count"] == 0
    assert payload["available_count"] == 0
    assert all(not row["configured"] and not row["available"] for row in payload["models"])


def test_availability_checker_skips_imports_when_disabled(monkeypatch, tmp_path: Path) -> None:
    example_path = tmp_path / "config" / "model_integrations" / "model_integrations.example.json"
    _write_config(example_path)
    monkeypatch.setattr(checker, "EXAMPLE_CONFIG_PATH", example_path)
    monkeypatch.setattr(checker, "LOCAL_CONFIG_PATH", tmp_path / "missing.local.json")

    import_calls: list[str] = []

    def _fake_import(name: str):  # noqa: ANN001
        import_calls.append(name)
        raise AssertionError("No optional import should run when all models are disabled")

    monkeypatch.setattr(checker.importlib, "import_module", _fake_import)
    payload = checker.evaluate_model_integrations()
    assert payload["configured_count"] == 0
    assert import_calls == []


def test_no_model_claims_configured_without_local_config(monkeypatch, tmp_path: Path) -> None:
    example_path = tmp_path / "config" / "model_integrations" / "model_integrations.example.json"
    _write_config(example_path, enabled_overrides={"moonbeam": True, "musicbert": True})
    monkeypatch.setattr(checker, "EXAMPLE_CONFIG_PATH", example_path)
    monkeypatch.setattr(checker, "LOCAL_CONFIG_PATH", tmp_path / "missing.local.json")
    payload = checker.evaluate_model_integrations()
    assert payload["using_local_config"] is False
    assert payload["configured_count"] == 0
    assert all(row["configured"] is False for row in payload["models"])


def test_no_model_claims_training_has_occurred() -> None:
    payload = checker.evaluate_model_integrations()
    assert payload["model_training_has_occurred"] is False


def test_policy_blocks_splice_training() -> None:
    decision = training_source_policy(source_name="splice", authorization_status="authorized")
    assert decision.allowed is False
    assert "blocked_splice" in decision.tags


def test_policy_blocks_unknown_authorization() -> None:
    decision = training_source_policy(source_name="local_dataset", authorization_status="unknown")
    assert decision.allowed is False
    assert "blocked_unknown_authorization" in decision.tags


def test_transcription_outputs_marked_witness_not_truth() -> None:
    decision = model_usage_policy("yourmt3")
    assert decision.allowed is True
    assert "witness_not_truth" in decision.tags


def test_audio_generation_models_reference_only_by_default() -> None:
    decision = model_usage_policy("musicgen")
    assert decision.allowed is False
    assert "reference_only" in decision.tags


def test_public_reports_contain_no_forward_slash_users_path(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(checker, "EXAMPLE_CONFIG_PATH", tmp_path / "config" / "model_integrations" / "model_integrations.example.json")
    _write_config(checker.EXAMPLE_CONFIG_PATH)
    monkeypatch.setattr(checker, "LOCAL_CONFIG_PATH", tmp_path / "config" / "model_integrations" / "model_integrations.local.json")
    _, md_path, _ = checker.write_model_integration_report(tmp_path / "reports" / "model_integrations")
    text = md_path.read_text(encoding="utf-8")
    assert "C:/Users" not in text


def test_public_reports_contain_no_backslash_users_path(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(checker, "EXAMPLE_CONFIG_PATH", tmp_path / "config" / "model_integrations" / "model_integrations.example.json")
    _write_config(checker.EXAMPLE_CONFIG_PATH)
    monkeypatch.setattr(checker, "LOCAL_CONFIG_PATH", tmp_path / "config" / "model_integrations" / "model_integrations.local.json")
    json_path, _, _ = checker.write_model_integration_report(tmp_path / "reports" / "model_integrations")
    text = json_path.read_text(encoding="utf-8")
    assert "C:\\Users" not in text


def test_local_config_is_git_ignored() -> None:
    gitignore = (Path(__file__).resolve().parents[1] / ".gitignore").read_text(encoding="utf-8")
    assert "config/model_integrations/*.local.json" in gitignore
