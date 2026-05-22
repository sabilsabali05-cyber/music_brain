from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.feature_dataset_common import now_iso, save_json
from scripts.trust_common import load_jsonl_records, resolve_performance_context, trust_dir


def _line_dump(record: dict[str, Any]) -> str:
    return json.dumps(record, ensure_ascii=True)


def _window_reliability_map(reliability_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    windows = reliability_payload.get("windows", [])
    if not isinstance(windows, list):
        return output
    for item in windows:
        if not isinstance(item, dict):
            continue
        window_id = str(item.get("window_id", ""))
        if window_id:
            output[window_id] = item
    return output


def _git_commit() -> str | None:
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        return result.stdout.strip() or None
    except Exception:  # noqa: BLE001
        return None


def export_training_dataset_splits(performance_manifest_path: Path) -> Path:
    ctx = resolve_performance_context(performance_manifest_path)
    feature_dir = ctx["feature_dir"]
    trust_output_dir = trust_dir(feature_dir)
    ai_path = feature_dir / "ai_training_records.jsonl"
    quality_path = trust_output_dir / "quality_gates.json"
    reliability_path = trust_output_dir / "transcription_reliability.json"
    ai_records = load_jsonl_records(ai_path)
    quality_payload = json.loads(quality_path.read_text(encoding="utf-8")) if quality_path.exists() else {}
    reliability_payload = json.loads(reliability_path.read_text(encoding="utf-8")) if reliability_path.exists() else {}
    window_rel = _window_reliability_map(reliability_payload if isinstance(reliability_payload, dict) else {})
    overall_status = str(quality_payload.get("overall_quality_status", "review_required"))

    export_root = Path("datasets") / "training_exports" / ctx["performance_id"] / ctx["segment_run_id"]
    export_root.mkdir(parents=True, exist_ok=True)

    split_records: dict[str, list[dict[str, Any]]] = {
        "accepted_records": [],
        "weak_label_records": [],
        "audio_midi_only_records": [],
        "review_required_records": [],
        "quarantined_records": [],
    }

    seen_ids: dict[str, str] = {}
    for record in ai_records:
        record_id = str(record.get("record_id", ""))
        if not record_id:
            split = "quarantined_records"
            split_records[split].append(record)
            continue

        window_id = str(record.get("window_id", "") or "")
        rel = window_rel.get(window_id, {})
        tier = str(rel.get("reliability_tier", "medium" if record.get("granularity") == "performance" else "low"))
        score = float(rel.get("transcription_reliability_score", 0.5) or 0.5)
        label_status = str(record.get("label_status", "weak_label"))
        review_required = bool(record.get("review_required", True))
        confidence = float(record.get("confidence", 0.0) or 0.0)
        has_required = all(field in record for field in ["record_id", "performance_id", "granularity", "start_seconds", "end_seconds"])

        split = "review_required_records"
        if not has_required or tier in {"failed", "missing"}:
            split = "quarantined_records"
        elif label_status in {"raw_observation", "derived_observation"} and tier in {"high", "medium"} and confidence >= 0.55 and not review_required:
            split = "accepted_records"
        elif label_status in {"weak_label", "heuristic_estimate", "interpretive_weak_label", "model_prediction"}:
            split = "weak_label_records" if tier in {"high", "medium"} and confidence >= 0.35 else "review_required_records"
        elif label_status == "human_verified_label":
            split = "accepted_records"
        elif tier in {"high", "medium"} and confidence >= 0.5:
            split = "audio_midi_only_records"
        elif tier == "low":
            split = "review_required_records"

        if overall_status == "quarantined" and split != "quarantined_records":
            split = "review_required_records" if split != "accepted_records" else "audio_midi_only_records"

        if record_id in seen_ids:
            split = "quarantined_records"
        seen_ids[record_id] = split
        split_records[split].append(record)

    for split_name, records in split_records.items():
        output_path = export_root / f"{split_name}.jsonl"
        lines = [_line_dump(record) for record in records]
        output_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    manifest = {
        "performance_id": ctx["performance_id"],
        "segment_run_id": ctx["segment_run_id"],
        "source_feature_pack_path": feature_dir.as_posix(),
        "created_at": now_iso(),
        "pipeline_git_commit": _git_commit(),
        "counts_per_split": {name: len(records) for name, records in split_records.items()},
        "inclusion_rules_used": {
            "accepted": "raw/derived observations with high or medium reliability and adequate confidence.",
            "weak_label": "heuristic/model weak labels retained separately.",
            "audio_midi_only": "usable timing/transcription context without safe labels.",
            "review_required": "ambiguous or low-confidence records needing review.",
            "quarantined": "missing/failed/malformed records or duplicate IDs.",
        },
        "limitations": [
            "Split assignment is heuristic and should be reviewed for production training.",
            "Quality gate status can down-rank records globally.",
        ],
    }
    save_json(export_root / "export_manifest.json", manifest)
    return export_root.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Export trusted training dataset splits for one performance.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    args = parser.parse_args()
    output = export_training_dataset_splits(Path(args.performance_manifest))
    print(f"TRAINING_EXPORT_DIR={output.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
