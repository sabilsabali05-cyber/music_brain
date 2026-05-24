from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.model_integrations.model_policy import transcription_witness_policy_state

LOCAL_CONFIG = ROOT_DIR / "config" / "model_integrations" / "model_integrations.local.json"
EXAMPLE_CONFIG = ROOT_DIR / "config" / "model_integrations" / "model_integrations.example.json"
REPORT_DIR = ROOT_DIR / "reports" / "model_integrations"
PLACEHOLDERS = {"", "<PATH_TO_MODEL>", "<PATH_TO_REPO>", "<DEVICE>"}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_models_config() -> tuple[dict[str, Any], bool]:
    if LOCAL_CONFIG.exists():
        payload = _load_json(LOCAL_CONFIG)
        using_local = True
    else:
        payload = _load_json(EXAMPLE_CONFIG)
        using_local = False
    models = payload.get("models", {}) if isinstance(payload, dict) else {}
    return models if isinstance(models, dict) else {}, using_local


def _is_real_value(value: Any) -> bool:
    return str(value or "").strip() not in PLACEHOLDERS


def _path_state(value: Any) -> dict[str, Any]:
    return {
        "configured": _is_real_value(value),
        "exists": Path(str(value)).exists() if _is_real_value(value) else False,
        "path": "<PRIVATE_LOCAL_PATH>",
    }


def _model_setup(settings: dict[str, Any], using_local: bool, model_id: str) -> dict[str, Any]:
    model_cfg = settings.get(model_id, {})
    model_cfg = model_cfg if isinstance(model_cfg, dict) else {}
    enabled = bool(model_cfg.get("enabled", False)) if using_local else False
    repo_ok = _is_real_value(model_cfg.get("repo_path"))
    model_ok = _is_real_value(model_cfg.get("model_path"))
    device_ok = _is_real_value(model_cfg.get("device"))
    configured = bool(using_local and enabled and repo_ok and model_ok and device_ok)

    if not using_local:
        reason = "disabled_or_missing_local_config"
        next_step = (
            "Copy config/model_integrations/model_integrations.example.json to "
            "config/model_integrations/model_integrations.local.json and keep both witnesses disabled by default."
        )
    elif not enabled:
        reason = "disabled_in_local_config"
        next_step = f"Set models.{model_id}.enabled=true only when you are ready for local witness-only checks."
    elif not repo_ok or not model_ok or not device_ok:
        reason = "enabled_but_paths_not_configured"
        next_step = f"Set models.{model_id}.repo_path, model_path, and device with non-placeholder local values."
    else:
        reason = "configured_but_execution_disabled_by_policy"
        next_step = (
            "Use an explicit future command with user-provided input to run witness inference; "
            "this vertical slice does not execute transcription."
        )

    return {
        "enabled": enabled,
        "configured": configured,
        "available": False,
        "unavailable_reason": reason,
        "next_setup_step": next_step,
        "path_checks": {
            "repo_path": _path_state(model_cfg.get("repo_path")),
            "model_path": _path_state(model_cfg.get("model_path")),
        },
    }


def evaluate_transcription_witnesses_setup() -> dict[str, Any]:
    models_cfg, using_local = _read_models_config()
    yourmt3 = _model_setup(models_cfg, using_local, "yourmt3")
    basic_pitch = _model_setup(models_cfg, using_local, "basic_pitch")
    policy = transcription_witness_policy_state()
    return {
        "status": "ok",
        "config_source": (
            "config/model_integrations/model_integrations.local.json"
            if using_local
            else "config/model_integrations/model_integrations.example.json"
        ),
        "yourmt3_configured": yourmt3["configured"],
        "yourmt3_available": policy["yourmt3_available"],
        "yourmt3_unavailable_reason": yourmt3["unavailable_reason"],
        "basic_pitch_configured": basic_pitch["configured"],
        "basic_pitch_available": policy["basic_pitch_available"],
        "basic_pitch_unavailable_reason": basic_pitch["unavailable_reason"],
        "transcription_performed": policy["transcription_performed"],
        "model_training_has_occurred": policy["model_training_has_occurred"],
        "witness_policy": policy["witness_policy"],
        "audio_processing_performed": False,
        "downloads_performed": False,
        "no_fake_transcription_outputs": True,
        "next_setup_step": yourmt3["next_setup_step"],
        "details": {
            "yourmt3": yourmt3,
            "basic_pitch": basic_pitch,
        },
        "limitations": [
            "Checker is setup-only and does not execute transcription.",
            "No audio is processed and no model weights are downloaded.",
            "Heavy imports are intentionally skipped in this vertical slice.",
        ],
    }


def write_transcription_witnesses_setup_report(output_dir: Path) -> tuple[Path, Path, dict[str, Any]]:
    payload = evaluate_transcription_witnesses_setup()
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "transcription_witnesses_setup_status.json"
    md_path = output_dir / "transcription_witnesses_setup_status.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = [
        "# Transcription Witnesses Setup Status",
        "",
        f"- config_source: `{payload['config_source']}`",
        f"- yourmt3_configured: `{payload['yourmt3_configured']}`",
        f"- yourmt3_available: `{payload['yourmt3_available']}`",
        f"- basic_pitch_configured: `{payload['basic_pitch_configured']}`",
        f"- basic_pitch_available: `{payload['basic_pitch_available']}`",
        f"- transcription_performed: `{payload['transcription_performed']}`",
        f"- witness_policy: `{payload['witness_policy']}`",
        "- model_training_has_occurred: `False`",
        "- audio_processing_performed: `False`",
        "- downloads_performed: `False`",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path, payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Check transcription witness setup without running transcription.")
    parser.add_argument("--output-dir", default=REPORT_DIR.as_posix())
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT_DIR / output_dir
    json_path, md_path, payload = write_transcription_witnesses_setup_report(output_dir)
    print(f"TRANSCRIPTION_WITNESSES_SETUP_JSON={json_path.as_posix()}")
    print(f"TRANSCRIPTION_WITNESSES_SETUP_MD={md_path.as_posix()}")
    print(f"YOURMT3_CONFIGURED={payload['yourmt3_configured']}")
    print(f"YOURMT3_AVAILABLE={payload['yourmt3_available']}")
    print(f"BASIC_PITCH_CONFIGURED={payload['basic_pitch_configured']}")
    print(f"BASIC_PITCH_AVAILABLE={payload['basic_pitch_available']}")
    print("TRANSCRIPTION_PERFORMED=False")
    print("MODEL_TRAINING_HAS_OCCURRED=False")
    print("WITNESS_POLICY=witness_not_truth")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
