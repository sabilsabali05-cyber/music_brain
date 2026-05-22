from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.feature_dataset_common import (
    default_feature_dir,
    get_active_paths,
    load_json,
    performance_metadata,
)


def resolve_performance_context(performance_manifest_path: Path) -> dict[str, Any]:
    performance_manifest = load_json(performance_manifest_path)
    segments_manifest_path, analysis_path, merged_midi_path = get_active_paths(performance_manifest)
    performance_id, source_name, segment_run_id = performance_metadata(performance_manifest, segments_manifest_path)
    feature_dir = default_feature_dir(performance_id, segment_run_id).resolve()
    return {
        "performance_manifest_path": performance_manifest_path.resolve(),
        "performance_manifest": performance_manifest,
        "segments_manifest_path": segments_manifest_path.resolve(),
        "analysis_path": analysis_path.resolve() if analysis_path and analysis_path.exists() else analysis_path,
        "merged_midi_path": merged_midi_path.resolve() if merged_midi_path and merged_midi_path.exists() else merged_midi_path,
        "performance_id": performance_id,
        "source_name": source_name,
        "segment_run_id": segment_run_id,
        "feature_dir": feature_dir,
    }


def trust_dir(feature_dir: Path) -> Path:
    output = feature_dir / "trust"
    output.mkdir(parents=True, exist_ok=True)
    return output


def load_jsonl_records(path: Path) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    if not path.exists():
        return output
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(parsed, dict):
            output.append(parsed)
    return output
