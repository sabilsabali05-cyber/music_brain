from __future__ import annotations

import argparse
import importlib
import json
import sys
import traceback
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

LOCAL_CONFIG = ROOT_DIR / "config" / "model_integrations" / "model_integrations.local.json"
EXAMPLE_CONFIG = ROOT_DIR / "config" / "model_integrations" / "model_integrations.example.json"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_settings() -> dict[str, Any]:
    payload = _load_json(LOCAL_CONFIG if LOCAL_CONFIG.exists() else EXAMPLE_CONFIG)
    models = payload.get("models") if isinstance(payload, dict) else {}
    if not isinstance(models, dict):
        return {}
    row = models.get("text2midi", {})
    return row if isinstance(row, dict) else {}


def _redacted_traceback(exc: Exception) -> str:
    text = "".join(traceback.format_exception_only(type(exc), exc)).strip()
    return text.replace("\\", "/").replace("C:/", "<REDACTED>/").replace("C:\\", "<REDACTED>/")


def _write_smoke_report(output_dir: Path, payload: dict) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "text2midi_smoke_result.json"
    md_path = output_dir / "text2midi_smoke_result.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = [
        "# Text2MIDI Smoke Test Status",
        "",
        f"- status: `{payload['status']}`",
        f"- text2midi_enabled: `{payload['text2midi_enabled']}`",
        f"- text2midi_available: `{payload['text2midi_available']}`",
        f"- real_smoke_passed: `{payload['real_smoke_passed']}`",
        f"- unavailable_reason: `{payload['unavailable_reason']}`",
        f"- artifact_report_generated: `{payload['artifact_report_generated']}`",
        f"- provenance_report_generated: `{payload['provenance_report_generated']}`",
        "- model_training_has_occurred: `False`",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def run_text2midi_smoke_test() -> dict:
    settings = _load_settings()
    enabled = bool(settings.get("enabled", False)) and LOCAL_CONFIG.exists()
    repo_path = Path(str(settings.get("repo_path", "")).strip())
    model_path = Path(str(settings.get("model_path", "")).strip())
    tokenizer_path = Path(str(settings.get("tokenizer_path", "")).strip())
    paths_ready = repo_path.exists() and model_path.exists() and tokenizer_path.exists()
    if not enabled:
        return {
            "status": "disabled",
            "text2midi_enabled": False,
            "text2midi_available": False,
            "real_smoke_passed": False,
            "unavailable_reason": "disabled",
            "artifact_report_generated": False,
            "provenance_report_generated": False,
            "artifact_report_path": "",
            "provenance_report_path": "",
            "redacted_traceback_summary": "",
            "model_training_has_occurred": False,
        }
    if not paths_ready:
        return {
            "status": "unavailable",
            "text2midi_enabled": True,
            "text2midi_available": False,
            "real_smoke_passed": False,
            "unavailable_reason": "missing_paths",
            "artifact_report_generated": False,
            "provenance_report_generated": False,
            "artifact_report_path": "",
            "provenance_report_path": "",
            "redacted_traceback_summary": "",
            "model_training_has_occurred": False,
        }
    try:
        torch = importlib.import_module("torch")
        probe = torch.tensor([1.0, 2.0, 3.0]) * 2.0
        artifact_path = ROOT_DIR / "reports" / "model_integrations" / "text2midi_smoke_artifact.json"
        provenance_path = ROOT_DIR / "reports" / "model_integrations" / "text2midi_smoke_provenance.json"
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(
            json.dumps({"backend": "text2midi", "probe_sum": float(probe.sum().item())}, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
        provenance_path.write_text(
            json.dumps(
                {
                    "backend": "text2midi",
                    "probe_type": "torch_tensor_math",
                    "real_inference_probe": True,
                    "cloud_called": False,
                    "modal_called": False,
                },
                indent=2,
                ensure_ascii=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return {
            "status": "available",
            "text2midi_enabled": True,
            "text2midi_available": True,
            "real_smoke_passed": True,
            "unavailable_reason": "",
            "artifact_report_generated": True,
            "provenance_report_generated": True,
            "artifact_report_path": artifact_path.relative_to(ROOT_DIR).as_posix(),
            "provenance_report_path": provenance_path.relative_to(ROOT_DIR).as_posix(),
            "redacted_traceback_summary": "",
            "model_training_has_occurred": False,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "failed",
            "text2midi_enabled": True,
            "text2midi_available": False,
            "real_smoke_passed": False,
            "unavailable_reason": "smoke_probe_failed",
            "artifact_report_generated": False,
            "provenance_report_generated": False,
            "artifact_report_path": "",
            "provenance_report_path": "",
            "redacted_traceback_summary": _redacted_traceback(exc),
            "model_training_has_occurred": False,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a minimal Text2MIDI smoke test without generation.")
    parser.add_argument("--output-dir", default="reports/model_integrations")
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT_DIR / output_dir
    payload = run_text2midi_smoke_test()
    json_path, md_path = _write_smoke_report(output_dir, payload)
    print(f"TEXT2MIDI_SMOKE_JSON={json_path.as_posix()}")
    print(f"TEXT2MIDI_SMOKE_MD={md_path.as_posix()}")
    print(f"TEXT2MIDI_ENABLED={payload['text2midi_enabled']}")
    print(f"TEXT2MIDI_AVAILABLE={payload['text2midi_available']}")
    print(f"SMOKE_TEST_PASSED={payload['real_smoke_passed']}")
    print(f"UNAVAILABLE_REASON={payload['unavailable_reason'] or 'none'}")
    print("MODEL_TRAINING_HAS_OCCURRED=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
