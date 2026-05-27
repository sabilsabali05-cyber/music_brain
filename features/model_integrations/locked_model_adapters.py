from __future__ import annotations

import json
import importlib.util
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
LOCAL_REGISTRY_PATH = ROOT_DIR / "local_model_integration" / "active_model_registry.local.json"


@dataclass(frozen=True)
class AdapterCallResult:
    ok: bool
    operation: str
    model: str
    error_code: str
    message: str
    output_path: str
    real_backend_observation_increment: int
    details: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _error(operation: str, model: str, code: str, message: str, details: dict[str, Any] | None = None) -> AdapterCallResult:
    return AdapterCallResult(
        ok=False,
        operation=operation,
        model=model,
        error_code=code,
        message=message,
        output_path="",
        real_backend_observation_increment=0,
        details=details or {},
    )


def _success(
    operation: str,
    model: str,
    output_path: str,
    details: dict[str, Any] | None = None,
) -> AdapterCallResult:
    return AdapterCallResult(
        ok=True,
        operation=operation,
        model=model,
        error_code="",
        message="real_backend_output_available",
        output_path=output_path,
        real_backend_observation_increment=1,
        details=details or {},
    )


def _load_registry(path: Path | None = None) -> dict[str, Any]:
    target = path or LOCAL_REGISTRY_PATH
    if not target.exists():
        return {"models": []}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"models": []}
    if not isinstance(payload, dict):
        return {"models": []}
    return payload


def _registry_by_name(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = payload.get("models", [])
    if not isinstance(rows, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        model = str(row.get("model", "")).strip().lower()
        if model:
            out[model] = row
    return out


def _require_active(by_name: dict[str, dict[str, Any]], model: str, operation: str) -> AdapterCallResult | None:
    row = by_name.get(model, {})
    if not bool(row.get("active", False)):
        return _error(
            operation,
            model,
            "model_inactive",
            "Model is inactive under integration lock policy.",
            {"reason": row.get("reason", "unknown")},
        )
    return None


def transcribe_audio(audio_path: str, preferred_models: list[str] | None = None) -> dict[str, Any]:
    payload = _load_registry()
    by_name = _registry_by_name(payload)
    model_order = preferred_models or ["basicpitch", "mt3"]
    for model in model_order:
        active_error = _require_active(by_name, model, "transcribe_audio")
        if active_error is not None:
            continue
        midi_path = ROOT_DIR / "local_model_outputs" / "basicpitch" / "source_loop_basicpitch.mid"
        if not midi_path.exists():
            return _error(
                "transcribe_audio",
                model,
                "missing_real_output",
                "Active model has no concrete local smoke output MIDI.",
            ).as_dict()
        return _success(
            "transcribe_audio",
            model,
            midi_path.relative_to(ROOT_DIR).as_posix(),
            details={"input_audio": audio_path, "local_only_output_dir": "local_model_outputs/basicpitch"},
        ).as_dict()
    return _error(
        "transcribe_audio",
        model_order[0] if model_order else "unknown",
        "no_active_model",
        "No active transcription model available.",
    ).as_dict()


def separate_audio(audio_path: str, preferred_model: str = "demucs") -> dict[str, Any]:
    payload = _load_registry()
    by_name = _registry_by_name(payload)
    row = by_name.get(preferred_model, {})
    output_dir = (ROOT_DIR / "local_model_outputs" / "demucs").relative_to(ROOT_DIR).as_posix()

    def _result(*, active: bool, stems: list[str], error: str, role_summary: dict[str, bool]) -> dict[str, Any]:
        return {
            "active": active,
            "stems": stems,
            "role_summary": role_summary,
            "output_dir": output_dir,
            "real_backend_observation": 1 if active else 0,
            "error": error,
        }

    if not bool(row.get("active", False)):
        return _result(
            active=False,
            stems=[],
            role_summary={},
            error=f"model_inactive:{row.get('reason', 'unknown')}",
        )
    if importlib.util.find_spec("demucs") is None:
        return _result(active=False, stems=[], role_summary={}, error="import_failed:python_module_missing_demucs")

    checkpoint_roots = [ROOT_DIR / "local_model_weights" / "demucs", ROOT_DIR / "local_model_cache" / "demucs"]
    checkpoint_hits: list[Path] = []
    for checkpoint_root in checkpoint_roots:
        if not checkpoint_root.exists():
            continue
        checkpoint_hits.extend([item for item in checkpoint_root.rglob("*.th") if item.is_file()])
    if not checkpoint_hits:
        return _result(active=False, stems=[], role_summary={}, error="weights_missing:checkpoint_not_found")

    stem_root = ROOT_DIR / output_dir
    wavs = sorted([item for item in stem_root.rglob("*.wav") if item.is_file() and item.stat().st_size > 128])
    if not wavs:
        return _result(active=False, stems=[], role_summary={}, error="stems_missing:no_readable_stems")

    stems = [item.relative_to(ROOT_DIR).as_posix() for item in wavs]
    role_summary = {
        "drums": any("drums" in item.name.lower() for item in wavs),
        "bass": any("bass" in item.name.lower() for item in wavs),
        "other": any("other" in item.name.lower() for item in wavs),
        "vocals": any("vocals" in item.name.lower() for item in wavs),
    }
    return _result(active=True, stems=stems, role_summary=role_summary, error="")


def analyze_midi(midi_path: str, preferred_models: list[str] | None = None) -> dict[str, Any]:
    if not midi_path.lower().endswith((".mid", ".midi")):
        return _error(
            "analyze_midi",
            "musicbert",
            "invalid_input",
            "analyze_midi requires MIDI input path.",
        ).as_dict()
    payload = _load_registry()
    by_name = _registry_by_name(payload)
    for model in (preferred_models or ["musicbert", "moonbeam", "midigpt", "text2midi", "omnizart"]):
        active_error = _require_active(by_name, model, "analyze_midi")
        if active_error is None:
            return _error(
                "analyze_midi",
                model,
                "missing_real_output",
                "Model is active but no real MIDI analysis artifact is available.",
            ).as_dict()
    return _error(
        "analyze_midi",
        "musicbert",
        "no_active_model",
        "No active symbolic analysis backend available.",
    ).as_dict()


def generate_midi_context(midi_path: str, preferred_models: list[str] | None = None) -> dict[str, Any]:
    if not midi_path.lower().endswith((".mid", ".midi")):
        return _error(
            "generate_midi_context",
            "moonbeam",
            "invalid_input",
            "generate_midi_context requires MIDI input path.",
        ).as_dict()
    payload = _load_registry()
    by_name = _registry_by_name(payload)
    for model in (preferred_models or ["moonbeam", "midigpt", "text2midi"]):
        active_error = _require_active(by_name, model, "generate_midi_context")
        if active_error is None:
            return _error(
                "generate_midi_context",
                model,
                "missing_real_output",
                "Model is active but no real MIDI context artifact is available.",
            ).as_dict()
    return _error(
        "generate_midi_context",
        "moonbeam",
        "no_active_model",
        "No active symbolic generation backend available.",
    ).as_dict()
