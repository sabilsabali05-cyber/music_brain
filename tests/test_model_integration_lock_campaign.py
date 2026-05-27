from __future__ import annotations

import json
import subprocess
from pathlib import Path

from features.model_integrations import locked_model_adapters as adapters
from scripts import run_model_integration_lock_campaign as campaign


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_lock_campaign_reports_are_parseable() -> None:
    campaign.run_lock_campaign()
    stems = [
        "model_integration_lock_plan",
        "model_environment_strategy",
        "basicpitch_integration_report",
        "demucs_integration_report",
        "mt3_integration_report",
        "omnizart_integration_report",
        "moonbeam_integration_report",
        "musicbert_integration_report",
        "midigpt_integration_report",
        "text2midi_integration_report",
        "active_model_registry_report",
        "model_integration_lock",
    ]
    for stem in stems:
        payload = _read_json(campaign.REPORT_DIR / f"{stem}.json")
        assert isinstance(payload, dict)
        assert payload


def test_basicpitch_activation_truthfulness() -> None:
    campaign.run_lock_campaign()
    payload = _read_json(campaign.REPORT_DIR / "basicpitch_integration_report.json")
    active = bool(payload.get("active", False))
    note_count = int(payload.get("note_count", 0))
    assert active is (note_count > 0)
    if active:
        midi_path = campaign.ROOT_DIR / str(payload["smoke_output_midi"])
        assert midi_path.exists()
        assert int(payload.get("real_backend_observation", 0)) == 1


def test_demucs_activation_truthfulness() -> None:
    campaign.run_lock_campaign()
    payload = _read_json(campaign.REPORT_DIR / "demucs_integration_report.json")
    active = bool(payload.get("active", False))
    stems = payload.get("readable_stems", [])
    if active:
        assert isinstance(stems, list) and stems
        for stem in stems:
            assert (campaign.ROOT_DIR / stem).exists()
    else:
        assert int(payload.get("real_backend_observation", 0)) == 0


def test_adapter_refuses_inactive_models(tmp_path: Path, monkeypatch) -> None:
    registry = {
        "models": [
            {"model": "basicpitch", "active": False, "reason": "locked"},
            {"model": "demucs", "active": False, "reason": "locked"},
            {"model": "moonbeam", "active": False, "reason": "locked"},
        ]
    }
    registry_path = tmp_path / "active_model_registry.local.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    monkeypatch.setattr(adapters, "LOCAL_REGISTRY_PATH", registry_path)

    tx = adapters.transcribe_audio("local_model_outputs/source_loop.wav")
    sep = adapters.separate_audio("local_model_outputs/source_loop.wav")
    assert tx["ok"] is False and tx["error_code"] in {"no_active_model", "model_inactive"}
    assert sep["active"] is False
    assert sep["error"].startswith("model_inactive:")
    assert tx["output_path"] == ""
    assert sep["real_backend_observation"] == 0
    assert sep["output_dir"] == "local_model_outputs/demucs"


def test_symbolic_and_audio_constraints_are_enforced() -> None:
    bad_analysis = adapters.analyze_midi("local_model_outputs/source_loop.wav")
    bad_context = adapters.generate_midi_context("local_model_outputs/source_loop.wav")
    assert bad_analysis["error_code"] == "invalid_input"
    assert bad_context["error_code"] == "invalid_input"


def test_reports_are_redacted_from_local_paths() -> None:
    campaign.run_lock_campaign()
    for report in campaign.REPORT_DIR.glob("*.json"):
        text = report.read_text(encoding="utf-8")
        assert "C:\\Users" not in text
        assert "C:/Users" not in text


def test_demucs_inactive_when_package_missing(tmp_path: Path, monkeypatch) -> None:
    registry_path = tmp_path / "active_model_registry.local.json"
    registry_path.write_text(json.dumps({"models": [{"model": "demucs", "active": True, "reason": ""}]}), encoding="utf-8")
    monkeypatch.setattr(adapters, "LOCAL_REGISTRY_PATH", registry_path)
    monkeypatch.setattr(adapters, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(adapters.importlib.util, "find_spec", lambda name: None)
    payload = adapters.separate_audio("local_model_outputs/source_loop.wav")
    assert payload["active"] is False
    assert payload["error"] == "import_failed:python_module_missing_demucs"
    assert payload["stems"] == []


def test_demucs_inactive_when_checkpoint_missing(tmp_path: Path, monkeypatch) -> None:
    registry_path = tmp_path / "active_model_registry.local.json"
    registry_path.write_text(json.dumps({"models": [{"model": "demucs", "active": True, "reason": ""}]}), encoding="utf-8")
    monkeypatch.setattr(adapters, "LOCAL_REGISTRY_PATH", registry_path)
    monkeypatch.setattr(adapters, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(adapters.importlib.util, "find_spec", lambda name: object())
    payload = adapters.separate_audio("local_model_outputs/source_loop.wav")
    assert payload["active"] is False
    assert payload["error"] == "weights_missing:checkpoint_not_found"
    assert payload["real_backend_observation"] == 0


def test_demucs_active_only_after_readable_stems(tmp_path: Path, monkeypatch) -> None:
    registry_path = tmp_path / "active_model_registry.local.json"
    registry_path.write_text(json.dumps({"models": [{"model": "demucs", "active": True, "reason": ""}]}), encoding="utf-8")
    monkeypatch.setattr(adapters, "LOCAL_REGISTRY_PATH", registry_path)
    monkeypatch.setattr(adapters, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(adapters.importlib.util, "find_spec", lambda name: object())
    weights_dir = tmp_path / "local_model_weights" / "demucs"
    weights_dir.mkdir(parents=True, exist_ok=True)
    (weights_dir / "htdemucs_test.th").write_bytes(b"checkpoint")

    missing_stem_payload = adapters.separate_audio("local_model_outputs/source_loop.wav")
    assert missing_stem_payload["active"] is False
    assert missing_stem_payload["error"] == "stems_missing:no_readable_stems"

    stem_root = tmp_path / "local_model_outputs" / "demucs" / "htdemucs" / "source_loop"
    stem_root.mkdir(parents=True, exist_ok=True)
    for stem in ["drums.wav", "bass.wav", "other.wav", "vocals.wav"]:
        (stem_root / stem).write_bytes(b"\x00" * 512)

    payload = adapters.separate_audio("local_model_outputs/source_loop.wav")
    assert payload["active"] is True
    assert payload["error"] == ""
    assert payload["real_backend_observation"] == 1
    assert payload["output_dir"] == "local_model_outputs/demucs"
    assert len(payload["stems"]) == 4
    assert payload["role_summary"] == {"drums": True, "bass": True, "other": True, "vocals": True}


def test_local_model_weight_and_cache_paths_are_not_tracked() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(["git", "ls-files"], cwd=repo_root, capture_output=True, text=True, check=False)
    assert result.returncode == 0
    tracked = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    assert not any(path.startswith("local_model_weights/") for path in tracked)
    assert not any(path.startswith("local_model_cache/") for path in tracked)


def test_basicpitch_registry_entry_remains_present() -> None:
    campaign.run_lock_campaign()
    payload = _read_json(campaign.REPORT_DIR / "active_model_registry_report.json")
    rows = [row for row in payload.get("models", []) if isinstance(row, dict)]
    basicpitch = next(row for row in rows if str(row.get("model", "")) == "basicpitch")
    assert "transcribe_audio" in str(basicpitch.get("adapter_path", ""))
