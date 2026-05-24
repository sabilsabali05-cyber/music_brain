from __future__ import annotations

import json
from pathlib import Path

from scripts import check_cloud_backends, plan_cloud_full_activation, run_cloud_full_activation


def _manifest() -> dict[str, object]:
    return {
        "manifest_version": 2,
        "execute": False,
        "allow_cloud_execution": False,
        "allow_cloud_upload": False,
        "allow_ableton_export": False,
        "training_allowed": False,
        "max_budget_usd": 0.0,
        "input_authorization": {"authorization_status": "unknown", "explicitly_authorized_for_execution": False},
        "inputs": [{"input_id": "example_input_1", "reference": "samples/input/.gitkeep"}],
        "models": {
            "demucs": {"enabled": False, "provider": "modal", "allow_execute": False},
            "essentia": {"enabled": False, "provider": "modal", "allow_execute": False},
            "muq": {"enabled": False, "provider": "modal", "allow_execute": False},
            "mert": {"enabled": False, "provider": "modal", "allow_execute": False},
            "yourmt3": {"enabled": False, "provider": "modal", "allow_execute": False},
            "basic_pitch": {"enabled": False, "provider": "modal", "allow_execute": False},
            "text2midi": {"enabled": False, "provider": "huggingface", "allow_execute": False},
            "moonbeam": {"enabled": False, "provider": "replicate", "allow_execute": False},
            "midigpt": {"enabled": False, "provider": "modal", "allow_execute": False},
            "musicbert": {"enabled": False, "provider": "modal", "allow_execute": False},
        },
    }


def _assert_never_performed(payload: dict[str, object]) -> None:
    assert payload["cloud_jobs_started"] is False
    assert payload["uploads_performed"] is False
    assert payload["downloads_performed"] is False
    assert payload["audio_processing_performed"] is False
    assert payload["source_separation_performed"] is False
    assert payload["transcription_performed"] is False
    assert payload["embeddings_generated"] is False
    assert payload["symbolic_generation_performed"] is False
    assert payload["ranking_performed"] is False
    assert payload["ableton_export_performed"] is False
    assert payload["training_performed"] is False


def test_cloud_backend_status_defaults_disabled() -> None:
    payload = check_cloud_backends.build_cloud_backend_status()
    assert payload["cloud_execution_available"] is False
    assert payload["provider_available_flags"]["modal"] is False
    assert payload["provider_available_flags"]["hf"] is False
    assert payload["provider_available_flags"]["replicate"] is False
    _assert_never_performed(payload)


def test_cloud_plan_defaults_to_planned_dry_run() -> None:
    payload = plan_cloud_full_activation.build_cloud_full_activation_plan(_manifest(), Path("manifest.json"))
    assert payload["status"] == "planned_dry_run"
    assert len(payload["stage_plan"]) == 14
    _assert_never_performed(payload)


def test_cloud_run_defaults_to_planned_dry_run() -> None:
    payload = run_cloud_full_activation.build_cloud_full_activation_run_report(_manifest(), Path("manifest.json"))
    assert payload["status"] == "planned_dry_run"
    assert payload["no_fake_output_guarantee"] is True
    _assert_never_performed(payload)


def test_public_reports_redact_private_paths_and_tokens(tmp_path: Path) -> None:
    payload = {
        **_manifest(),
        "manifest_path": "C:/Users/example/private/path.json",
        "api_url": "https://x.example/a?X-Amz-Signature=secret",
        "bucket_path": "s3://private-bucket/path",
        "token_hint": "MODAL_TOKEN should never leak",
    }
    json_path = tmp_path / "x.json"
    md_path = tmp_path / "x.md"
    from scripts.cloud_full_activation_common import write_public_report

    write_public_report(payload=payload, json_path=json_path, md_path=md_path, title="t", bullets=["safe"])
    text = json_path.read_text(encoding="utf-8") + md_path.read_text(encoding="utf-8")
    assert "C:/Users/" not in text
    assert "C:\\Users\\" not in text
    assert "X-Amz-Signature" not in text
    assert "s3://" not in text
    assert "MODAL_TOKEN" not in text
    assert "HF_TOKEN" not in text
    assert "REPLICATE_API_TOKEN" not in text
    json.loads(json_path.read_text(encoding="utf-8"))
