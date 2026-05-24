from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.model_integrations.model_policy import source_separation_witness_policy_state
from features.source_separation.demucs_adapter import demucs_unavailable_safe

LOCAL_CONFIG = ROOT_DIR / "config" / "model_integrations" / "model_integrations.local.json"
EXAMPLE_CONFIG = ROOT_DIR / "config" / "model_integrations" / "model_integrations.example.json"
REPORT_DIR = ROOT_DIR / "reports" / "model_integrations"


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


def evaluate_source_separation_setup() -> dict[str, Any]:
    models_cfg, using_local = _read_models_config()
    demucs_status = demucs_unavailable_safe(models_cfg, using_local)
    policy = source_separation_witness_policy_state()
    return {
        "status": "ok",
        "config_source": (
            "config/model_integrations/model_integrations.local.json"
            if using_local
            else "config/model_integrations/model_integrations.example.json"
        ),
        "demucs_configured": demucs_status.configured,
        "demucs_available": policy["demucs_available"],
        "smoke_test_passed": False,
        "source_separation_performed": policy["source_separation_performed"],
        "stems_generated": policy["stems_generated"],
        "downloads_performed": policy["downloads_performed"],
        "model_training_has_occurred": policy["model_training_has_occurred"],
        "witness_policy": policy["witness_policy"],
        "training_use_allowed": policy["training_use_allowed"],
        "demucs_unavailable_reason": demucs_status.unavailable_reason,
        "demucs_details": demucs_status.as_dict(),
        "audio_processing_performed": False,
        "limitations": [
            "Setup check is witness-only and does not process audio.",
            "No stem separation is executed and no downloads are performed.",
            "Stem outputs are weak evidence and never ground truth.",
        ],
        "next_setup_step": (
            "Copy config/model_integrations/model_integrations.example.json to "
            "config/model_integrations/model_integrations.local.json, then set "
            "models.demucs.enabled=true only when explicit witness execution is intentionally enabled."
        ),
    }


def write_source_separation_setup_report(output_dir: Path) -> tuple[Path, Path, dict[str, Any]]:
    payload = evaluate_source_separation_setup()
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "source_separation_setup_status.json"
    md_path = output_dir / "source_separation_setup_status.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = [
        "# Source Separation Setup Status",
        "",
        f"- config_source: `{payload['config_source']}`",
        f"- demucs_configured: `{payload['demucs_configured']}`",
        f"- demucs_available: `{payload['demucs_available']}`",
        "- smoke_test_passed: `False`",
        "- source_separation_performed: `False`",
        "- stems_generated: `False`",
        "- downloads_performed: `False`",
        "- model_training_has_occurred: `False`",
        f"- witness_policy: `{payload['witness_policy']}`",
        "- training_use_allowed: `false_by_default`",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path, payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Check source separation witness setup without separating stems.")
    parser.add_argument("--output-dir", default=REPORT_DIR.as_posix())
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT_DIR / output_dir
    json_path, md_path, payload = write_source_separation_setup_report(output_dir)
    print(f"SOURCE_SEPARATION_SETUP_JSON={json_path.as_posix()}")
    print(f"SOURCE_SEPARATION_SETUP_MD={md_path.as_posix()}")
    print(f"DEMUCS_CONFIGURED={payload['demucs_configured']}")
    print("DEMUCS_AVAILABLE=False")
    print("SMOKE_TEST_PASSED=False")
    print("SOURCE_SEPARATION_PERFORMED=False")
    print("STEMS_GENERATED=False")
    print("DOWNLOADS_PERFORMED=False")
    print("MODEL_TRAINING_HAS_OCCURRED=False")
    print("WITNESS_POLICY=weak_evidence_not_truth")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
