from __future__ import annotations

import json
from pathlib import Path

from scripts import plan_full_model_activation, run_full_model_activation


def _manifest(*, execute: bool = False, authorized: bool = False) -> dict[str, object]:
    return {
        "manifest_version": 1,
        "execute": execute,
        "training_allowed": False,
        "human_review_required": True,
        "export_training_dataset": False,
        "allow_flags": {
            "allow_audio_processing": execute,
            "allow_source_separation": execute,
            "allow_transcription": execute,
            "allow_embeddings": execute,
            "allow_symbolic_generation": execute,
            "allow_training_export": False,
        },
        "inputs": [
            {
                "input_id": "x1",
                "kind": "full_mix_audio",
                "source_policy": "authorized_user_owned",
                "authorization_status": "authorized_for_processing" if authorized else "unknown",
                "explicitly_authorized_for_execution": authorized,
                "reference": "samples/input/.gitkeep",
            }
        ],
        "models": {
            "demucs": {"enabled": True, "required_for_execution": False, "allow_execute": True},
            "yourmt3": {"enabled": True, "required_for_execution": False, "allow_execute": True},
            "basic_pitch": {"enabled": False, "required_for_execution": False, "allow_execute": False},
            "muq": {"enabled": False, "required_for_execution": False, "allow_execute": False},
            "mert": {"enabled": False, "required_for_execution": False, "allow_execute": False},
            "essentia": {"enabled": False, "required_for_execution": False, "allow_execute": False},
            "moonbeam": {"enabled": False, "required_for_execution": False, "allow_execute": False},
            "midigpt": {"enabled": False, "required_for_execution": False, "allow_execute": False},
            "text2midi": {"enabled": False, "required_for_execution": False, "allow_execute": False},
            "musicbert": {"enabled": False, "required_for_execution": False, "allow_execute": False},
        },
    }


def _assert_dry_flags(payload: dict[str, object]) -> None:
    assert payload["audio_processing_performed"] is False
    assert payload["source_separation_performed"] is False
    assert payload["transcription_performed"] is False
    assert payload["embeddings_generated"] is False
    assert payload["symbolic_generation_performed"] is False
    assert payload["training_performed"] is False


def test_plan_defaults_to_planned_dry_run() -> None:
    payload = plan_full_model_activation.build_activation_plan(_manifest(), Path("manifest.json"))
    assert payload["status"] == "planned"
    _assert_dry_flags(payload)
    assert payload["validation_passed"] is True
    assert payload["no_modal_calls_performed"] is True
    assert payload["model_weights_downloaded"] is False
    assert payload["provenance_outputs"] == []


def test_plan_rejects_execute_when_input_unauthorized() -> None:
    payload = plan_full_model_activation.build_activation_plan(_manifest(execute=True, authorized=False), Path("m.json"))
    assert payload["execute"] is True
    assert payload["unauthorized_inputs"]


def test_run_default_dry_run_has_no_processing() -> None:
    payload = run_full_model_activation.build_run_report(_manifest(execute=False), Path("manifest.json"))
    assert payload["status"] == "dry_run"
    assert payload["execute_allowed"] is False
    _assert_dry_flags(payload)


def test_run_execute_rejected_when_unauthorized() -> None:
    payload = run_full_model_activation.build_run_report(_manifest(execute=True, authorized=False), Path("manifest.json"))
    assert payload["status"] == "rejected_unauthorized_inputs"
    assert payload["validation_passed"] is False
    assert any("unauthorized" in err for err in payload["validation_errors"])
    _assert_dry_flags(payload)


def test_run_marks_unavailable_models_without_fallback() -> None:
    payload = run_full_model_activation.build_run_report(_manifest(execute=True, authorized=True), Path("manifest.json"))
    model_rows = payload["model_routing"]
    assert any(row["status"] == "skipped_unavailable" for row in model_rows if row["model_id"] in {"demucs", "yourmt3"})
    assert payload["no_silent_fallback"] is True


def test_training_export_requires_dual_authorization() -> None:
    manifest = _manifest(execute=False)
    manifest["export_training_dataset"] = True
    manifest["training_allowed"] = False
    manifest["human_review_required"] = False
    payload = plan_full_model_activation.build_activation_plan(manifest, Path("m.json"))
    assert payload["training_export_authorized"] is False


def test_plan_report_redacts_private_paths(tmp_path: Path) -> None:
    payload = plan_full_model_activation.build_activation_plan(_manifest(), Path("C:/Users/izzyo/private.json"))
    json_path, md_path = plan_full_model_activation.write_report(
        payload=payload,
        json_path=tmp_path / "plan.json",
        md_path=tmp_path / "plan.md",
        title="t",
        bullets=["private test"],
    )
    text = json_path.read_text(encoding="utf-8") + md_path.read_text(encoding="utf-8")
    assert "C:/Users/izzyo" not in text
    assert "C:\\Users\\izzyo" not in text
    assert json.loads(json_path.read_text(encoding="utf-8"))["manifest_path"].startswith("<PRIVATE_USERS_PATH>")
