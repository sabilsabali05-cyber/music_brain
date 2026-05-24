from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT_DIR / "config" / "model_integrations"
EXAMPLE_CONFIG = CONFIG_DIR / "model_integrations.example.json"
LOCAL_CONFIG = CONFIG_DIR / "model_integrations.local.json"
REPORT_DIR = ROOT_DIR / "reports" / "model_integrations"

SYMBOLIC_BACKENDS = ("text2midi", "moonbeam", "midigpt", "musicbert")
PLACEHOLDER_PATH = "<PRIVATE_LOCAL_PATH>"
PLACEHOLDER_DEVICE = "<DEVICE>"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def _default_backend_settings(backend_id: str) -> dict[str, Any]:
    settings: dict[str, Any] = {
        "enabled": False,
        "repo_path": PLACEHOLDER_PATH,
        "model_path": PLACEHOLDER_PATH,
        "tokenizer_path": PLACEHOLDER_PATH,
        "device": PLACEHOLDER_DEVICE,
        "smoke_test_enabled": False,
    }
    return settings


def bootstrap_local_config() -> dict[str, Any]:
    if LOCAL_CONFIG.exists():
        payload = _load_json(LOCAL_CONFIG)
        created = False
    else:
        payload = _load_json(EXAMPLE_CONFIG)
        created = True
    if not isinstance(payload, dict):
        payload = {}
    models = payload.get("models")
    if not isinstance(models, dict):
        models = {}
    payload["models"] = models
    for backend_id in SYMBOLIC_BACKENDS:
        existing = models.get(backend_id)
        if not isinstance(existing, dict):
            existing = {}
        defaults = _default_backend_settings(backend_id)
        merged = {**defaults, **existing}
        merged["enabled"] = bool(merged.get("enabled", False))
        models[backend_id] = merged
    LOCAL_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_CONFIG.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    all_enabled = all(bool(models[b].get("enabled", False)) for b in SYMBOLIC_BACKENDS)
    report_payload = {
        "status": "ok",
        "local_config_created_or_exists": True,
        "local_config_was_created": created,
        "all_models_enabled": all_enabled,
        "private_paths_redacted": True,
        "symbolic_backends": {
            backend_id: {
                "enabled": bool(models[backend_id].get("enabled", False)),
                "repo_path_configured": str(models[backend_id].get("repo_path", "")).strip()
                not in {"", PLACEHOLDER_PATH},
                "model_path_configured": str(models[backend_id].get("model_path", "")).strip()
                not in {"", PLACEHOLDER_PATH},
                "tokenizer_path_configured": (
                    str(models[backend_id].get("tokenizer_path", "")).strip() not in {"", PLACEHOLDER_PATH}
                    if "tokenizer_path" in models[backend_id]
                    else None
                ),
            }
            for backend_id in SYMBOLIC_BACKENDS
        },
        "model_training_has_occurred": False,
        "trained_model_generation_allowed": False,
    }
    return report_payload


def write_report(payload: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "symbolic_activation_config_status.json"
    md_path = output_dir / "symbolic_activation_config_status.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = [
        "# Symbolic Activation Config Status",
        "",
        f"- local_config_created_or_exists: `{payload['local_config_created_or_exists']}`",
        f"- local_config_was_created: `{payload['local_config_was_created']}`",
        f"- all_models_enabled: `{payload['all_models_enabled']}`",
        f"- private_paths_redacted: `{payload['private_paths_redacted']}`",
        "- model_training_has_occurred: `False`",
        "- trained_model_generation_allowed: `False`",
        "",
        "## Backends",
    ]
    for backend_id in SYMBOLIC_BACKENDS:
        row = payload["symbolic_backends"][backend_id]
        lines.append(
            f"- `{backend_id}` enabled=`{row['enabled']}` "
            f"repo_configured=`{row['repo_path_configured']}` "
            f"model_configured=`{row['model_path_configured']}` "
            f"tokenizer_configured=`{row['tokenizer_path_configured']}`"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap symbolic model local config safely.")
    parser.add_argument("--output-dir", default=REPORT_DIR.as_posix())
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT_DIR / output_dir
    payload = bootstrap_local_config()
    json_path, md_path = write_report(payload, output_dir)
    print(f"SYMBOLIC_CONFIG_BOOTSTRAP_JSON={json_path.as_posix()}")
    print(f"SYMBOLIC_CONFIG_BOOTSTRAP_MD={md_path.as_posix()}")
    print("LOCAL_CONFIG_CREATED_OR_EXISTS=True")
    print(f"ALL_MODELS_ENABLED={payload['all_models_enabled']}")
    print("PRIVATE_PATHS_REDACTED=True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
