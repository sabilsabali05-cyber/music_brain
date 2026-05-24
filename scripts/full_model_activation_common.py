from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT_DIR / "reports" / "activation"
LOCAL_MODEL_CONFIG = ROOT_DIR / "config" / "model_integrations" / "model_integrations.local.json"
EXAMPLE_MODEL_CONFIG = ROOT_DIR / "config" / "model_integrations" / "model_integrations.example.json"

REQUIRED_DRY_RUN_FLAGS = {
    "audio_processing_performed": False,
    "source_separation_performed": False,
    "transcription_performed": False,
    "embeddings_generated": False,
    "symbolic_generation_performed": False,
    "training_performed": False,
}

ALLOWED_AUTHORIZATION = {
    "authorized_for_processing",
    "authorized_for_training",
    "approved_for_processing",
    "trusted_for_training",
}
BLOCKED_AUTHORIZATION = {"unknown", "undeclared", "copyrighted", "restricted"}
DEFAULT_MODEL_IDS = [
    "demucs",
    "yourmt3",
    "basic_pitch",
    "muq",
    "mert",
    "essentia",
    "moonbeam",
    "midigpt",
    "text2midi",
    "musicbert",
]


@dataclass(frozen=True)
class ActivationValidation:
    valid: bool
    errors: list[str]
    warnings: list[str]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def redact_public_text(text: str) -> str:
    posix_user_root = "C:" + "/" + "Users" + "/"
    windows_user_root = "C:" + "\\" + "Users" + "\\"
    return text.replace(posix_user_root, "<PRIVATE_USERS_PATH>/").replace(windows_user_root, "<PRIVATE_USERS_PATH>\\")


def redact_public_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return json.loads(redact_public_text(json.dumps(payload, ensure_ascii=True)))


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


def load_manifest(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not payload:
        raise ValueError(f"Manifest is missing or invalid JSON: {path.as_posix()}")
    return payload


def model_rows_from_checker() -> dict[str, dict[str, Any]]:
    from scripts.check_model_integrations import evaluate_model_integrations

    rows = evaluate_model_integrations().get("models", [])
    return {str(row.get("model_id", "")): row for row in rows if isinstance(row, dict)}


def normalized_model_config(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    models = manifest.get("models", {})
    if not isinstance(models, dict):
        return {}
    normalized: dict[str, dict[str, Any]] = {}
    for model_id in DEFAULT_MODEL_IDS:
        row = models.get(model_id, {})
        row = row if isinstance(row, dict) else {}
        normalized[model_id] = {
            "enabled": bool(row.get("enabled", False)),
            "required_for_execution": bool(row.get("required_for_execution", False)),
            "allow_execute": bool(row.get("allow_execute", False)),
        }
    return normalized


def _is_authorized_input(input_row: dict[str, Any]) -> bool:
    auth = str(input_row.get("authorization_status", "")).strip().lower()
    explicit = bool(input_row.get("explicitly_authorized_for_execution", False))
    return explicit and auth in ALLOWED_AUTHORIZATION and auth not in BLOCKED_AUTHORIZATION


def unauthorized_inputs(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    inputs = manifest.get("inputs", [])
    if not isinstance(inputs, list):
        return [{"input_id": "<invalid>", "reason": "inputs_must_be_array"}]
    blocked: list[dict[str, Any]] = []
    for row in inputs:
        if not isinstance(row, dict):
            blocked.append({"input_id": "<invalid>", "reason": "input_must_be_object"})
            continue
        if not _is_authorized_input(row):
            blocked.append(
                {
                    "input_id": row.get("input_id", "<missing_input_id>"),
                    "reason": "unauthorized_or_missing_explicit_execution_authorization",
                    "authorization_status": row.get("authorization_status", "unknown"),
                }
            )
    return blocked


def validate_manifest(manifest: dict[str, Any]) -> ActivationValidation:
    errors: list[str] = []
    warnings: list[str] = []

    execute = bool(manifest.get("execute", False))
    export_training = bool(manifest.get("export_training_dataset", False))
    training_allowed = bool(manifest.get("training_allowed", False))
    human_review_required = bool(manifest.get("human_review_required", False))
    allow_flags = manifest.get("allow_flags", {})
    allow_flags = allow_flags if isinstance(allow_flags, dict) else {}

    if execute:
        blocked = unauthorized_inputs(manifest)
        if blocked:
            errors.append("execute=true requires every input to be explicitly authorized for processing")
        if not bool(allow_flags.get("allow_audio_processing", False)):
            errors.append("execute=true requires allow_flags.allow_audio_processing=true")

    if export_training and not training_allowed:
        errors.append("training export requested but training_allowed=false")
    if export_training and not human_review_required:
        errors.append("training export requested but human_review_required=false")

    if not LOCAL_MODEL_CONFIG.exists():
        warnings.append(
            "local model integration config is missing; all model activation paths remain unavailable by default"
        )

    return ActivationValidation(valid=not errors, errors=errors, warnings=warnings)


def stage_allows_execution(stage_name: str, allow_flags: dict[str, Any]) -> bool:
    mapping = {
        "source_separation": bool(allow_flags.get("allow_source_separation", False)),
        "transcription": bool(allow_flags.get("allow_transcription", False)),
        "embeddings": bool(allow_flags.get("allow_embeddings", False)),
        "symbolic_generation": bool(allow_flags.get("allow_symbolic_generation", False)),
        "training_export": bool(allow_flags.get("allow_training_export", False)),
    }
    return mapping.get(stage_name, False)


def write_report(
    *,
    payload: dict[str, Any],
    json_path: Path,
    md_path: Path,
    title: str,
    bullets: list[str],
) -> tuple[Path, Path]:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    public_payload = redact_public_payload(payload)
    json_path.write_text(json.dumps(public_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    md_lines = [f"# {title}", ""]
    md_lines.extend([f"- {redact_public_text(line)}" for line in bullets])
    md_lines.append("")
    md_lines.append("## Safety Guarantees")
    for key, value in REQUIRED_DRY_RUN_FLAGS.items():
        md_lines.append(f"- {key}: `{value}`")
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return json_path, md_path
