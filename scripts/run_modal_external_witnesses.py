from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.external_analyzer_common import external_output_dir, parse_provider_list, resolve_performance_context
from scripts.feature_dataset_common import load_json, save_json


def _read_local_artifact_bytes(path: Path | None) -> bytes | None:
    if path is None:
        return None
    if not path.exists():
        return None
    return path.read_bytes()


def _resolve_audio_path_from_manifest(performance_manifest: dict[str, Any]) -> Path | None:
    source_path = str(performance_manifest.get("source_path") or "").strip()
    if not source_path:
        return None
    path = Path(source_path)
    return path if path.exists() else None


def _ensure_status_payload(provider: str, payload: dict[str, Any] | None, source_name: str) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    return {
        "provider_name": provider,
        "status": "failed",
        "warnings": ["empty witness payload"],
        "limitations": ["Modal witness returned no structured payload."],
        "created_at": None,
        "source_artifacts": {"source_name": source_name},
    }


def _invoke_modal_provider(provider: str, payload_bytes: bytes, source_name: str) -> dict[str, Any]:
    import modal  # type: ignore[import-not-found]
    import external_witness_modal_app as witness_app

    with witness_app.app.run():
        if provider == "essentia":
            return witness_app.run_essentia_witness.remote(payload_bytes, source_name, {})
        if provider == "music21":
            return witness_app.run_music21_witness.remote(payload_bytes, source_name, {})
    return {
        "provider_name": provider,
        "status": "skipped",
        "warnings": ["provider not supported by modal witness app"],
        "limitations": [],
        "created_at": None,
        "source_artifacts": {"source_name": source_name},
    }


def run_modal_external_witnesses(performance_manifest_path: Path, providers: list[str]) -> dict[str, Any]:
    ctx = resolve_performance_context(performance_manifest_path)
    perf_manifest = ctx["performance_manifest"]
    feature_dir = ctx["feature_dir"]
    out_dir = external_output_dir(feature_dir)
    source_name = str(ctx["source_name"])
    audio_path = _resolve_audio_path_from_manifest(perf_manifest)
    midi_path = ctx["merged_midi_path"] if isinstance(ctx["merged_midi_path"], Path) else None

    provider_results: dict[str, dict[str, Any]] = {}
    for provider in providers:
        provider = provider.strip().lower()
        if not provider:
            continue
        if provider == "essentia":
            payload_bytes = _read_local_artifact_bytes(audio_path)
            if payload_bytes is None:
                payload = {
                    "provider_name": "essentia",
                    "status": "unavailable",
                    "warnings": ["source audio path is missing for witness run"],
                    "limitations": ["No local source audio available."],
                    "created_at": None,
                    "source_artifacts": {"source_name": source_name},
                }
            else:
                try:
                    payload = _ensure_status_payload("essentia", _invoke_modal_provider("essentia", payload_bytes, source_name), source_name)
                except Exception as exc:  # noqa: BLE001
                    payload = {
                        "provider_name": "essentia",
                        "status": "failed",
                        "warnings": [f"Modal witness invocation failed: {exc.__class__.__name__}: {exc}"],
                        "limitations": ["Invocation failure is non-fatal."],
                        "created_at": None,
                        "source_artifacts": {"source_name": source_name},
                    }
            out_path = out_dir / "essentia_features.json"
            save_json(out_path, payload)
            provider_results["essentia"] = {"status": payload.get("status", "failed"), "path": out_path.resolve().as_posix()}
            continue

        if provider == "music21":
            payload_bytes = _read_local_artifact_bytes(midi_path)
            if payload_bytes is None:
                payload = {
                    "provider_name": "music21",
                    "status": "unavailable",
                    "warnings": ["merged MIDI is missing for witness run"],
                    "limitations": ["No local merged MIDI available."],
                    "created_at": None,
                    "source_artifacts": {"source_name": source_name},
                }
            else:
                try:
                    payload = _ensure_status_payload("music21", _invoke_modal_provider("music21", payload_bytes, source_name), source_name)
                except Exception as exc:  # noqa: BLE001
                    payload = {
                        "provider_name": "music21",
                        "status": "failed",
                        "warnings": [f"Modal witness invocation failed: {exc.__class__.__name__}: {exc}"],
                        "limitations": ["Invocation failure is non-fatal."],
                        "created_at": None,
                        "source_artifacts": {"source_name": source_name},
                    }
            out_path = out_dir / "music21_features.json"
            save_json(out_path, payload)
            provider_results["music21"] = {"status": payload.get("status", "failed"), "path": out_path.resolve().as_posix()}
            continue

        # Optional providers: probe only, do not fail the pipeline.
        out_path = out_dir / f"{provider}_availability.json"
        payload = {
            "provider_name": provider,
            "status": "skipped",
            "warnings": ["Provider not implemented in modal witness runner yet."],
            "limitations": ["Optional provider probe only."],
            "created_at": None,
            "source_artifacts": {"source_name": source_name},
        }
        save_json(out_path, payload)
        provider_results[provider] = {"status": "skipped", "path": out_path.resolve().as_posix()}

    manifest_path = feature_dir / "feature_pack_manifest.json"
    if manifest_path.exists():
        manifest = load_json(manifest_path)
        refs = manifest.get("external_model_feature_refs", {})
        if not isinstance(refs, dict):
            refs = {}
        for _, result in provider_results.items():
            refs[Path(str(result.get("path", ""))).stem] = result.get("path")
        manifest["external_model_feature_refs"] = refs
        manifest["external_feature_refs"] = refs
        save_json(manifest_path, manifest)

    return {
        "performance_id": ctx["performance_id"],
        "segment_run_id": ctx["segment_run_id"],
        "output_dir": out_dir.resolve().as_posix(),
        "results": provider_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Modal external witness providers for an existing performance run.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    parser.add_argument("--providers", default="essentia,music21", help="Comma-separated providers")
    args = parser.parse_args()
    providers = parse_provider_list(args.providers)
    summary = run_modal_external_witnesses(Path(args.performance_manifest), providers)
    print("MODAL_EXTERNAL_WITNESS_SUMMARY=" + json.dumps(summary, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
