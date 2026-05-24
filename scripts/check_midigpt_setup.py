from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

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


def _read_midigpt_config() -> tuple[dict[str, Any], bool]:
    if LOCAL_CONFIG.exists():
        payload = _load_json(LOCAL_CONFIG)
        using_local = True
    else:
        payload = _load_json(EXAMPLE_CONFIG)
        using_local = False
    models = payload.get("models", {}) if isinstance(payload, dict) else {}
    if not isinstance(models, dict):
        return {}, using_local
    settings = models.get("midigpt", {})
    return settings if isinstance(settings, dict) else {}, using_local


def _is_real_value(value: Any) -> bool:
    text = str(value or "").strip()
    return text not in PLACEHOLDERS


def _is_existing_path(value: Any) -> bool:
    text = str(value or "").strip()
    if not _is_real_value(text):
        return False
    return Path(text).exists()


def _redacted_path_state(value: Any) -> dict[str, Any]:
    text = str(value or "").strip()
    if not text:
        return {"configured": False, "exists": False, "path": "<PRIVATE_LOCAL_PATH>"}
    return {
        "configured": _is_real_value(text),
        "exists": _is_existing_path(text),
        "path": "<PRIVATE_LOCAL_PATH>",
    }


def evaluate_midigpt_setup() -> dict[str, Any]:
    settings, using_local_config = _read_midigpt_config()
    enabled = bool(settings.get("enabled", False))
    smoke_test_enabled = bool(settings.get("smoke_test_enabled", False))
    repo_ok = _is_existing_path(settings.get("repo_path"))
    model_ok = _is_existing_path(settings.get("model_path"))
    tokenizer_ok = _is_existing_path(settings.get("tokenizer_path"))
    midigpt_configured = using_local_config and enabled and repo_ok and model_ok and tokenizer_ok

    if not using_local_config:
        unavailable_reason = "disabled_or_missing_local_config"
        next_setup_step = (
            "Copy config/model_integrations/model_integrations.example.json to "
            "config/model_integrations/model_integrations.local.json, then set models.midigpt.enabled=true."
        )
    elif not enabled:
        unavailable_reason = "disabled_in_local_config"
        next_setup_step = "Set models.midigpt.enabled=true in local config after policy review."
    elif not repo_ok:
        unavailable_reason = "repo_path_missing"
        next_setup_step = "Set models.midigpt.repo_path to an existing local MIDI-GPT repository path."
    elif not model_ok:
        unavailable_reason = "model_path_missing"
        next_setup_step = "Set models.midigpt.model_path to an existing local model path."
    elif not tokenizer_ok:
        unavailable_reason = "tokenizer_path_missing"
        next_setup_step = "Set models.midigpt.tokenizer_path to an existing local tokenizer path."
    elif not smoke_test_enabled:
        unavailable_reason = "smoke_test_disabled_in_config"
        next_setup_step = "Set models.midigpt.smoke_test_enabled=true to allow local smoke validation."
    else:
        unavailable_reason = "ready_for_smoke_test"
        next_setup_step = "Run scripts/dev.cmd run-midigpt-smoke-test to validate local MIDI-GPT setup."

    return {
        "status": "ok",
        "config_source": (
            "config/model_integrations/model_integrations.local.json"
            if using_local_config
            else "config/model_integrations/model_integrations.example.json"
        ),
        "midigpt_enabled": enabled if using_local_config else False,
        "midigpt_configured": midigpt_configured,
        "midigpt_available": False,
        "smoke_test_enabled": smoke_test_enabled if using_local_config else False,
        "smoke_test_passed": False,
        "unavailable_reason": unavailable_reason,
        "next_setup_step": next_setup_step,
        "path_checks": {
            "repo_path": _redacted_path_state(settings.get("repo_path")),
            "model_path": _redacted_path_state(settings.get("model_path")),
            "tokenizer_path": _redacted_path_state(settings.get("tokenizer_path")),
        },
        "model_training_has_occurred": False,
        "limitations": [
            "No heavyweight MIDI-GPT package imports are attempted unless local config is enabled.",
            "No model weights are downloaded by this checker.",
            "No training is performed.",
        ],
    }


def write_midigpt_setup_report(output_dir: Path) -> tuple[Path, Path, dict[str, Any]]:
    payload = evaluate_midigpt_setup()
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "midigpt_setup_status.json"
    md_path = output_dir / "midigpt_setup_status.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = [
        "# MIDI-GPT Setup Status",
        "",
        f"- config_source: `{payload['config_source']}`",
        f"- midigpt_configured: `{payload['midigpt_configured']}`",
        f"- midigpt_available: `{payload['midigpt_available']}`",
        f"- smoke_test_passed: `{payload['smoke_test_passed']}`",
        f"- unavailable_reason: `{payload['unavailable_reason']}`",
        f"- next_setup_step: {payload['next_setup_step']}",
        "- model_training_has_occurred: `False`",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path, payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Check MIDI-GPT local setup readiness without heavy imports.")
    parser.add_argument("--output-dir", default=REPORT_DIR.as_posix())
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT_DIR / output_dir
    json_path, md_path, payload = write_midigpt_setup_report(output_dir)
    print(f"MIDIGPT_SETUP_STATUS_JSON={json_path.as_posix()}")
    print(f"MIDIGPT_SETUP_STATUS_MD={md_path.as_posix()}")
    print(f"MIDIGPT_CONFIGURED={payload['midigpt_configured']}")
    print(f"MIDIGPT_AVAILABLE={payload['midigpt_available']}")
    print(f"SMOKE_TEST_PASSED={payload['smoke_test_passed']}")
    print(f"UNAVAILABLE_REASON={payload['unavailable_reason']}")
    print("MODEL_TRAINING_HAS_OCCURRED=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
