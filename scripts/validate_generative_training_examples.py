from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.generative.task_policies import TASK_POLICIES
from scripts.feature_dataset_common import resolve_artifact_performance_dir


VALID_SPLITS = {"train", "validation", "review", "exclude"}
MAX_ARRAY_LEN = 256


def _resolve_dataset_folder(path: Path) -> Path:
    if path.exists():
        return path
    parts = list(path.parts)
    if len(parts) < 2:
        return path
    run_id = parts[-1]
    perf_id = parts[-2]
    compact_root = path.parent.parent.parent if len(parts) >= 3 else path.parent
    compact = resolve_artifact_performance_dir(compact_root, perf_id) / run_id
    return compact if compact.exists() else path


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path) -> tuple[list[dict[str, Any]], int]:
    if not path.exists():
        return [], 0
    rows: list[dict[str, Any]] = []
    errors = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except Exception:  # noqa: BLE001
            errors += 1
            continue
        if isinstance(parsed, dict):
            rows.append(parsed)
        else:
            errors += 1
    return rows, errors


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:  # noqa: BLE001
        return fallback


def _path_exists(path_text: Any) -> bool:
    if not isinstance(path_text, str) or not path_text.strip():
        return False
    try:
        return Path(path_text).exists()
    except Exception:  # noqa: BLE001
        return False


def _scan_large_arrays(value: Any, *, path: str = "root", hits: list[str] | None = None) -> list[str]:
    if hits is None:
        hits = []
    if isinstance(value, list):
        if len(value) > MAX_ARRAY_LEN:
            hits.append(f"{path} length={len(value)}")
        for idx, item in enumerate(value[: min(len(value), MAX_ARRAY_LEN + 1)]):
            _scan_large_arrays(item, path=f"{path}[{idx}]", hits=hits)
    elif isinstance(value, dict):
        for key, child in value.items():
            _scan_large_arrays(child, path=f"{path}.{key}", hits=hits)
    return hits


def validate_generative_training_examples(dataset_folder: Path) -> dict[str, Any]:
    dataset_folder = _resolve_dataset_folder(dataset_folder)
    errors: list[str] = []
    warnings: list[str] = []
    manifest_path = dataset_folder / "generative_manifest.json"
    jsonl_path = dataset_folder / "generative_examples.jsonl"
    summary_path = dataset_folder / "generative_summary.md"

    if not manifest_path.exists():
        errors.append("missing generative_manifest.json")
    if not jsonl_path.exists():
        errors.append("missing generative_examples.jsonl")
    if not summary_path.exists():
        warnings.append("missing generative_summary.md")

    manifest = _read_json(manifest_path) if manifest_path.exists() else {}
    rows, parse_errors = _read_jsonl(jsonl_path) if jsonl_path.exists() else ([], 0)
    if parse_errors > 0:
        errors.append(f"jsonl parse errors: {parse_errors}")

    for idx, row in enumerate(rows):
        task_type = str(row.get("task_type", ""))
        if task_type not in TASK_POLICIES:
            errors.append(f"row {idx}: invalid task_type={task_type}")
        split = str(row.get("split_recommendation", ""))
        if split not in VALID_SPLITS:
            errors.append(f"row {idx}: invalid split_recommendation={split}")

        for name in (
            "context_start_seconds",
            "context_end_seconds",
            "target_start_seconds",
            "target_end_seconds",
            "start_seconds",
            "end_seconds",
        ):
            if name not in row:
                errors.append(f"row {idx}: missing {name}")
        c_start = _safe_float(row.get("context_start_seconds"), -1.0)
        c_end = _safe_float(row.get("context_end_seconds"), -1.0)
        t_start = _safe_float(row.get("target_start_seconds"), -1.0)
        t_end = _safe_float(row.get("target_end_seconds"), -1.0)
        if not (c_start < c_end and t_start < t_end):
            errors.append(f"row {idx}: invalid context/target ranges")

        if not row.get("quality_score") or not isinstance(row.get("quality_score"), dict):
            errors.append(f"row {idx}: missing quality_score")
        else:
            final_score = _safe_float(row["quality_score"].get("final_score"), -1.0)
            if final_score < 0:
                errors.append(f"row {idx}: invalid quality_score.final_score")
            if final_score < 0.72 and split == "train":
                errors.append(f"row {idx}: low-quality example cannot be split=train")
            if final_score < 0.60 and split == "validation":
                errors.append(f"row {idx}: low-quality example cannot be split=validation")

        if not isinstance(row.get("split_reason_codes"), list):
            errors.append(f"row {idx}: missing split_reason_codes")
        if not isinstance(row.get("failed_policy_checks"), list):
            errors.append(f"row {idx}: missing failed_policy_checks")
        if not isinstance(row.get("missing_refs"), list):
            errors.append(f"row {idx}: missing missing_refs")
        if not isinstance(row.get("quality_component_breakdown"), dict):
            errors.append(f"row {idx}: missing quality_component_breakdown")

        if not _path_exists(row.get("target_midi_ref")):
            errors.append(f"row {idx}: missing target_midi_ref path")
        if not _path_exists(row.get("full_midi_ref")):
            errors.append(f"row {idx}: missing full_midi_ref path")

        feature_refs = row.get("feature_refs")
        if not isinstance(feature_refs, dict):
            errors.append(f"row {idx}: missing feature_refs")
        else:
            required_refs = ("rhythm_features", "harmony_features")
            for name in required_refs:
                if not _path_exists(feature_refs.get(name)):
                    warnings.append(f"row {idx}: feature ref missing/unavailable {name}")

        conditioning = row.get("conditioning")
        if isinstance(conditioning, dict):
            if "style_tags_ground_truth" in conditioning:
                errors.append(f"row {idx}: style_tags_ground_truth is not allowed")
        else:
            errors.append(f"row {idx}: missing conditioning")

        large_hits = _scan_large_arrays(row)
        if large_hits:
            errors.append(f"row {idx}: huge embedded arrays detected: {large_hits[:4]}")

    if manifest:
        expected = int(manifest.get("generative_examples_count", -1))
        if expected >= 0 and expected != len(rows):
            errors.append(
                f"manifest count mismatch: expected={expected} actual={len(rows)}"
            )

    return {
        "status": "success" if not errors else "failed",
        "dataset_folder": dataset_folder.resolve().as_posix(),
        "errors": errors,
        "warnings": warnings,
        "example_count": len(rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate generated generative-training examples folder.")
    parser.add_argument("generative_dataset_folder", help="Path to one generative dataset folder")
    args = parser.parse_args()
    summary = validate_generative_training_examples(Path(args.generative_dataset_folder))
    print("GENERATIVE_VALIDATION=" + json.dumps(summary, ensure_ascii=True))
    return 0 if summary["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())

