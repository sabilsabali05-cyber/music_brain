from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from features.cloud_execution.cloud_artifact_policy import redact_public_payload, redact_public_text
from features.cloud_execution.cloud_backend_schema import load_cloud_backend_config
from features.cloud_execution.cloud_provider_registry import evaluate_all_providers

ROOT_DIR = Path(__file__).resolve().parent.parent
CLOUD_REPORTS_DIR = ROOT_DIR / "reports" / "cloud_execution"
MUSIC_COGNITION_REPORTS_DIR = ROOT_DIR / "reports" / "music_cognition"
ACTIVATION_REPORTS_DIR = ROOT_DIR / "reports" / "activation"
LOCAL_MANIFEST_PATH = ROOT_DIR / "config" / "activation_manifests" / "full_cloud_activation.local.json"
EXAMPLE_MANIFEST_PATH = ROOT_DIR / "config" / "activation_manifests" / "full_cloud_activation.example.json"

CLOUD_STAGES = [
    "source_separation_demucs",
    "audio_embedding_essentia",
    "audio_embedding_muq",
    "audio_embedding_mert",
    "transcription_witness_yourmt3",
    "transcription_witness_basic_pitch",
    "symbolic_generation_text2midi",
    "symbolic_generation_moonbeam",
    "symbolic_generation_midigpt",
    "ranking_musicbert",
    "voice_interaction_graph",
    "ableton_export_plan",
    "ableton_export",
    "training",
]

REQUIRED_FALSE_FLAGS = {
    "cloud_jobs_started": False,
    "uploads_performed": False,
    "downloads_performed": False,
    "audio_processing_performed": False,
    "source_separation_performed": False,
    "transcription_performed": False,
    "embeddings_generated": False,
    "symbolic_generation_performed": False,
    "ranking_performed": False,
    "ableton_export_performed": False,
    "training_performed": False,
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


def load_activation_manifest(path_value: str | None) -> tuple[Path, dict[str, Any]]:
    if path_value:
        path = Path(path_value)
        if not path.is_absolute():
            path = ROOT_DIR / path
    else:
        path = LOCAL_MANIFEST_PATH if LOCAL_MANIFEST_PATH.exists() else EXAMPLE_MANIFEST_PATH
    payload = read_json(path)
    if not payload:
        raise ValueError(f"Invalid or missing activation manifest: {path.as_posix()}")
    return path, payload


def write_public_report(*, payload: dict[str, Any], json_path: Path, md_path: Path, title: str, bullets: list[str]) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    public_payload = redact_public_payload(payload)
    json_path.write_text(json.dumps(public_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = [f"# {title}", ""]
    lines.extend([f"- {redact_public_text(line)}" for line in bullets])
    lines.extend(["", "## Safety defaults"])
    for key, value in REQUIRED_FALSE_FLAGS.items():
        lines.append(f"- {key}: `{value}`")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def provider_status_rows() -> dict[str, dict[str, Any]]:
    backend = load_cloud_backend_config()
    return {key: row.as_dict() for key, row in evaluate_all_providers(backend).items()}
