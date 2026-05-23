from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.model_integrations.model_registry import model_registry_by_id

PLACEHOLDERS = {"<PATH_TO_MODEL>", "<PATH_TO_REPO>", "<DEVICE>", ""}
LOCAL_CONFIG_PATH = ROOT_DIR / "config" / "model_integrations" / "model_integrations.local.json"
EXAMPLE_CONFIG_PATH = ROOT_DIR / "config" / "model_integrations" / "model_integrations.example.json"

OPTIONAL_IMPORT_PROBES = {
    "demucs": "demucs",
    "basic_pitch": "basic_pitch",
    "essentia": "essentia",
}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def _select_config() -> tuple[dict[str, Any], bool]:
    if LOCAL_CONFIG_PATH.exists():
        return _load_json(LOCAL_CONFIG_PATH), True
    return _load_json(EXAMPLE_CONFIG_PATH), False


def _has_real_value(value: Any) -> bool:
    text = str(value or "").strip()
    return text not in PLACEHOLDERS


def _next_setup_step(model_id: str, configured: bool, using_local_config: bool, reason: str) -> str:
    if not using_local_config:
        return (
            "Copy config/model_integrations/model_integrations.example.json to "
            "config/model_integrations/model_integrations.local.json and enable this model explicitly."
        )
    if not configured:
        return f"Set models.{model_id}.enabled=true in local config after policy review."
    if reason == "enabled_but_paths_not_configured":
        return f"Set models.{model_id}.model_path, repo_path, and device with non-placeholder values."
    if reason == "optional_dependency_missing":
        return "Install optional lightweight runtime dependency manually, then re-run this checker."
    return "Run model-specific smoke test once local config and dependencies are ready."


def _probe_configured_backend(model_id: str, model_cfg: dict[str, Any]) -> tuple[bool, str]:
    model_path_ready = _has_real_value(model_cfg.get("model_path"))
    repo_path_ready = _has_real_value(model_cfg.get("repo_path"))
    device_ready = _has_real_value(model_cfg.get("device"))
    if not (model_path_ready and repo_path_ready and device_ready):
        return False, "enabled_but_paths_not_configured"

    probe_module = OPTIONAL_IMPORT_PROBES.get(model_id)
    if not probe_module:
        return False, "configured_but_smoke_probe_not_registered"
    try:
        importlib.import_module(probe_module)
    except ModuleNotFoundError:
        return False, "optional_dependency_missing"
    except Exception:  # noqa: BLE001
        return False, "optional_dependency_probe_failed"
    return True, "configured_dependency_probe_ok"


def evaluate_model_integrations() -> dict[str, Any]:
    config_payload, using_local_config = _select_config()
    configured_models = config_payload.get("models", {})
    if not isinstance(configured_models, dict):
        configured_models = {}

    registry = model_registry_by_id()
    rows: list[dict[str, Any]] = []
    configured_count = 0
    available_count = 0
    for model_id in sorted(registry.keys()):
        record = registry[model_id]
        model_cfg = configured_models.get(model_id, {})
        model_cfg = model_cfg if isinstance(model_cfg, dict) else {}
        configured = bool(model_cfg.get("enabled", False)) and using_local_config
        configured_count += int(configured)

        if configured:
            available, reason = _probe_configured_backend(model_id, model_cfg)
        else:
            available = False
            reason = "disabled_by_default_no_local_config" if not using_local_config else "disabled_in_local_config"
        available_count += int(available)

        rows.append(
            {
                "model_id": model_id,
                "family": record.family,
                "role": record.role_in_music_brain,
                "configured": configured,
                "available": available,
                "reason": reason,
                "next_setup_step": _next_setup_step(model_id, configured, using_local_config, reason),
                "smoke_test_supported": record.smoke_test_supported,
                "safety_policy": record.safety_policy,
                "training_allowed": record.training_allowed,
                "fine_tune_possible": record.fine_tune_possible,
            }
        )

    return {
        "status": "ok",
        "using_local_config": using_local_config,
        "config_source": (
            "config/model_integrations/model_integrations.local.json"
            if using_local_config
            else "config/model_integrations/model_integrations.example.json"
        ),
        "model_count": len(rows),
        "configured_count": configured_count,
        "available_count": available_count,
        "model_training_has_occurred": False,
        "models": rows,
        "limitations": [
            "No heavyweight dependencies are imported unless a backend is explicitly enabled in local config.",
            "No model downloads are triggered by this checker.",
            "Absence of optional models does not fail this checker.",
        ],
    }


def write_model_integration_report(output_dir: Path) -> tuple[Path, Path, dict[str, Any]]:
    payload = evaluate_model_integrations()
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "model_integration_availability.json"
    md_path = output_dir / "model_integration_availability.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    lines = [
        "# Model Integration Availability",
        "",
        f"- config_source: `{payload['config_source']}`",
        f"- configured_count: `{payload['configured_count']}`",
        f"- available_count: `{payload['available_count']}`",
        "- model_training_has_occurred: `False`",
        "",
        "## Model Status",
    ]
    for row in payload["models"]:
        lines.append(
            f"- `{row['model_id']}` configured=`{row['configured']}` available=`{row['available']}` "
            f"reason=`{row['reason']}` role=`{row['role']}`"
        )
        lines.append(f"  - next_setup_step: {row['next_setup_step']}")
    lines.extend(["", "## Limitations"])
    lines.extend([f"- {item}" for item in payload["limitations"]])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path, payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Check broader model integration availability.")
    parser.add_argument("--output-dir", default="reports/model_integrations")
    args = parser.parse_args()
    json_path, md_path, payload = write_model_integration_report(ROOT_DIR / args.output_dir)
    print(f"MODEL_INTEGRATION_AVAILABILITY_JSON={json_path.as_posix()}")
    print(f"MODEL_INTEGRATION_AVAILABILITY_MD={md_path.as_posix()}")
    print(f"MODEL_INTEGRATION_CONFIGURED_COUNT={payload['configured_count']}")
    print(f"MODEL_INTEGRATION_AVAILABLE_COUNT={payload['available_count']}")
    print("MODEL_TRAINING_HAS_OCCURRED=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
