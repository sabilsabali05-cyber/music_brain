from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT_DIR / "config" / "model_integrations" / "model_integrations.local.json"
REPORT_DIR = ROOT_DIR / "reports" / "model_integrations"
SMOKE_REPORT_FILES = {
    "moonbeam": ROOT_DIR / "reports" / "model_integrations" / "moonbeam_smoke_result.json",
    "musicbert": ROOT_DIR / "reports" / "model_integrations" / "musicbert_smoke_result.json",
    "midigpt": ROOT_DIR / "reports" / "model_integrations" / "midigpt_smoke_result.json",
    "text2midi": ROOT_DIR / "reports" / "model_integrations" / "text2midi_smoke_result.json",
}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def evaluate_activation_status() -> dict[str, Any]:
    config_payload = _load_json(CONFIG_PATH)
    models = config_payload.get("models") if isinstance(config_payload, dict) else {}
    if not isinstance(models, dict):
        models = {}

    backend_rows: dict[str, dict[str, bool]] = {}
    for backend_id, smoke_path in SMOKE_REPORT_FILES.items():
        model_cfg = models.get(backend_id, {})
        enabled = bool(model_cfg.get("enabled", False)) if isinstance(model_cfg, dict) else False
        smoke_payload = _load_json(smoke_path)
        smoke_status = str(smoke_payload.get("status", "missing"))
        available = smoke_status == "available"
        smoke_passed = available and bool(smoke_payload.get("real_smoke_passed", False))
        backend_rows[backend_id] = {
            "enabled": enabled,
            "available": available,
            "smoke_passed": smoke_passed,
        }

    generation_ready = any(
        backend_rows[name]["available"] for name in ("text2midi", "moonbeam", "midigpt")
    )
    ranking_ready = backend_rows["musicbert"]["available"]
    return {
        "status": "ok",
        "moonbeam_enabled": backend_rows["moonbeam"]["enabled"],
        "moonbeam_available": backend_rows["moonbeam"]["available"],
        "moonbeam_smoke_passed": backend_rows["moonbeam"]["smoke_passed"],
        "musicbert_enabled": backend_rows["musicbert"]["enabled"],
        "musicbert_available": backend_rows["musicbert"]["available"],
        "musicbert_smoke_passed": backend_rows["musicbert"]["smoke_passed"],
        "midigpt_enabled": backend_rows["midigpt"]["enabled"],
        "midigpt_available": backend_rows["midigpt"]["available"],
        "midigpt_smoke_passed": backend_rows["midigpt"]["smoke_passed"],
        "text2midi_enabled": backend_rows["text2midi"]["enabled"],
        "text2midi_available": backend_rows["text2midi"]["available"],
        "text2midi_smoke_passed": backend_rows["text2midi"]["smoke_passed"],
        "cloud_symbolic_available": False,
        "models_ready_for_generation": generation_ready,
        "models_ready_for_ranking": ranking_ready,
        "trained_model_generation_allowed": False,
        "model_training_has_occurred": False,
    }


def write_activation_report(output_dir: Path, payload: dict[str, Any]) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "symbolic_backend_activation_status.json"
    md_path = output_dir / "symbolic_backend_activation_status.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = [
        "# Symbolic Backend Activation Status",
        "",
        f"- moonbeam_enabled: `{payload['moonbeam_enabled']}`",
        f"- moonbeam_available: `{payload['moonbeam_available']}`",
        f"- moonbeam_smoke_passed: `{payload['moonbeam_smoke_passed']}`",
        f"- musicbert_enabled: `{payload['musicbert_enabled']}`",
        f"- musicbert_available: `{payload['musicbert_available']}`",
        f"- musicbert_smoke_passed: `{payload['musicbert_smoke_passed']}`",
        f"- midigpt_enabled: `{payload['midigpt_enabled']}`",
        f"- midigpt_available: `{payload['midigpt_available']}`",
        f"- midigpt_smoke_passed: `{payload['midigpt_smoke_passed']}`",
        f"- text2midi_enabled: `{payload['text2midi_enabled']}`",
        f"- text2midi_available: `{payload['text2midi_available']}`",
        f"- text2midi_smoke_passed: `{payload['text2midi_smoke_passed']}`",
        f"- cloud_symbolic_available: `{payload['cloud_symbolic_available']}`",
        f"- models_ready_for_generation: `{payload['models_ready_for_generation']}`",
        f"- models_ready_for_ranking: `{payload['models_ready_for_ranking']}`",
        "- trained_model_generation_allowed: `False`",
        "- model_training_has_occurred: `False`",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Check symbolic backend activation status.")
    parser.add_argument("--output-dir", default=REPORT_DIR.as_posix())
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT_DIR / output_dir
    payload = evaluate_activation_status()
    json_path, md_path = write_activation_report(output_dir, payload)
    print(f"SYMBOLIC_BACKEND_ACTIVATION_STATUS_JSON={json_path.as_posix()}")
    print(f"SYMBOLIC_BACKEND_ACTIVATION_STATUS_MD={md_path.as_posix()}")
    print(f"MODELS_READY_FOR_GENERATION={payload['models_ready_for_generation']}")
    print(f"MODELS_READY_FOR_RANKING={payload['models_ready_for_ranking']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
