from __future__ import annotations

from pathlib import Path
from typing import Any

from features.external_analyzers.registry import run_external_analyzers
from scripts.feature_dataset_common import (
    default_feature_dir,
    get_active_paths,
    load_json,
    now_iso,
    performance_metadata,
    save_json,
)


def parse_provider_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [item.strip().lower() for item in raw.split(",") if item.strip()]


def resolve_performance_context(performance_manifest_path: Path) -> dict[str, Any]:
    performance_manifest = load_json(performance_manifest_path)
    segments_manifest_path, analysis_path, merged_midi_path = get_active_paths(performance_manifest)
    performance_id, source_name, segment_run_id = performance_metadata(performance_manifest, segments_manifest_path)
    return {
        "performance_manifest_path": performance_manifest_path.resolve(),
        "performance_manifest": performance_manifest,
        "segments_manifest_path": segments_manifest_path.resolve(),
        "analysis_path": analysis_path.resolve() if analysis_path else None,
        "merged_midi_path": merged_midi_path.resolve() if merged_midi_path and merged_midi_path.exists() else None,
        "performance_id": performance_id,
        "source_name": source_name,
        "segment_run_id": segment_run_id,
        "feature_dir": default_feature_dir(performance_id, segment_run_id).resolve(),
    }


def resolve_authorized_audio_path(performance_manifest: dict[str, Any]) -> Path:
    source_path = str(performance_manifest.get("source_path") or "").strip()
    if not source_path:
        raise RuntimeError("Performance manifest is missing source_path.")
    if source_path.startswith(("http://", "https://")):
        raise RuntimeError("External analyzers only accept authorized local audio paths.")
    audio_path = Path(source_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio source not found: {audio_path}")
    return audio_path.resolve()


def external_output_dir(feature_dir: Path) -> Path:
    output = feature_dir / "external_model_features"
    output.mkdir(parents=True, exist_ok=True)
    return output


def _essentia_payload(result: dict[str, Any]) -> dict[str, Any]:
    features = result.get("features", {}) if isinstance(result.get("features"), dict) else {}
    return {
        "provider_name": "essentia",
        "status": result.get("status"),
        "audio_descriptors": features.get("audio_descriptors", {}),
        "rhythm_descriptors": features.get("rhythm_descriptors", {}),
        "tonal_descriptors": features.get("tonal_descriptors", {}),
        "spectral_descriptors": features.get("spectral_descriptors", {}),
        "high_level_descriptors": features.get("high_level_descriptors", {}),
        "model_outputs": features.get("model_outputs", {}),
        "warnings": result.get("warnings", []),
        "limitations": result.get("limitations", []),
        "created_at": result.get("created_at", now_iso()),
        "source_artifacts": result.get("source_artifacts", {}),
        "dependency_info": result.get("dependency_info", {}),
    }


def _musicnn_payload(result: dict[str, Any]) -> dict[str, Any]:
    features = result.get("features", {}) if isinstance(result.get("features"), dict) else {}
    return {
        "provider_name": "musicnn",
        "status": result.get("status"),
        "top_tags": features.get("top_tags", []),
        "tag_scores": features.get("tag_scores", {}),
        "embedding_reference": features.get("embedding_reference"),
        "embedding_summary": features.get("embedding_summary", {}),
        "model_info": features.get("model_info", {}),
        "warnings": result.get("warnings", []),
        "limitations": result.get("limitations", []),
        "created_at": result.get("created_at", now_iso()),
        "source_artifacts": result.get("source_artifacts", {}),
        "dependency_info": result.get("dependency_info", {}),
    }


def result_to_provider_payload(provider_name: str, result: dict[str, Any]) -> dict[str, Any]:
    if provider_name == "essentia":
        return _essentia_payload(result)
    if provider_name == "musicnn":
        return _musicnn_payload(result)
    return {
        "provider_name": provider_name,
        "status": result.get("status", "failed"),
        "warnings": result.get("warnings", []),
        "limitations": result.get("limitations", []),
        "created_at": result.get("created_at", now_iso()),
        "source_artifacts": result.get("source_artifacts", {}),
        "dependency_info": result.get("dependency_info", {}),
    }


def _provider_output_path(output_dir: Path, provider_name: str) -> Path:
    if provider_name == "essentia":
        return output_dir / "essentia_features.json"
    if provider_name == "musicnn":
        return output_dir / "musicnn_features.json"
    return output_dir / f"{provider_name}_features.json"


def run_and_write_external_analyzers(
    performance_manifest_path: Path,
    *,
    selected_providers: list[str] | None = None,
) -> dict[str, Any]:
    ctx = resolve_performance_context(performance_manifest_path)
    performance_manifest = ctx["performance_manifest"]
    audio_path = resolve_authorized_audio_path(performance_manifest)
    target_dir = external_output_dir(ctx["feature_dir"])

    run_context = {
        "performance_id": ctx["performance_id"],
        "segment_run_id": ctx["segment_run_id"],
        "performance_manifest_path": str(ctx["performance_manifest_path"]),
        "analysis_path": str(ctx["analysis_path"]) if ctx["analysis_path"] else None,
        "segments_manifest_path": str(ctx["segments_manifest_path"]),
        "merged_midi_path": str(ctx["merged_midi_path"]) if ctx["merged_midi_path"] else None,
    }
    raw_results = run_external_analyzers(audio_path, run_context, selected=selected_providers)

    results: dict[str, dict[str, Any]] = {}
    for result in raw_results:
        result_dict = result.__dict__
        provider_name = str(result.provider_name)
        payload = result_to_provider_payload(provider_name, result_dict)
        path = _provider_output_path(target_dir, provider_name)
        save_json(path, payload)
        results[provider_name] = {
            "status": payload.get("status"),
            "path": path.resolve().as_posix(),
            "warnings": payload.get("warnings", []),
            "limitations": payload.get("limitations", []),
        }

    manifest_path = ctx["feature_dir"] / "feature_pack_manifest.json"
    if manifest_path.exists():
        manifest = load_json(manifest_path)
        refs = manifest.get("external_feature_refs", {})
        if not isinstance(refs, dict):
            refs = {}
        for provider_name, meta in results.items():
            refs[f"{provider_name}_features"] = meta["path"]
        manifest["external_feature_refs"] = refs
        save_json(manifest_path, manifest)

    return {
        "performance_id": ctx["performance_id"],
        "segment_run_id": ctx["segment_run_id"],
        "audio_path": audio_path.as_posix(),
        "external_output_dir": target_dir.resolve().as_posix(),
        "results": results,
    }
