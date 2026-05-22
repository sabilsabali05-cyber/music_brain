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
from features.trust.field_trust_policy import (
    POLICY_VERSION,
    classify_record_for_export,
    make_accepted_observation_record,
    make_review_required_record,
    make_weak_label_record,
)


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

    excluded_field_summary: dict[str, int] = {}
    for idx, record in enumerate(ai_records):
        source_record_id = str(record.get("record_id", f"source_{idx:06d}"))
        classification = classify_record_for_export(record, window_rel, quality_payload if isinstance(quality_payload, dict) else {})
        split = str(classification.get("split", "review_required_records"))
        tier = str(classification.get("tier", "low"))
        weight = float(classification.get("weight", 0.0) or 0.0)
        reasons = [str(item) for item in classification.get("reasons", [])] if isinstance(classification.get("reasons"), list) else []

        if split == "quarantined_records":
            export_record = {
                **record,
                "export_record_id": f"{source_record_id}:quarantine:0",
                "source_record_id": source_record_id,
                "export_split": split,
                "trust_tier": tier,
                "training_weight": weight,
                "inclusion_reason": "; ".join(reasons) if reasons else "quarantine conditions met",
                "excluded_fields": [],
            }
            split_records[split].append(export_record)
            continue

        accepted_observation, excluded_fields = make_accepted_observation_record(record, window_rel)
        for field_name in excluded_fields:
            excluded_field_summary[field_name] = excluded_field_summary.get(field_name, 0) + 1

        weak_label_record = make_weak_label_record(record)
        review_record = make_review_required_record(record, reasons)

        can_emit_observation = tier in {"high", "medium"} and float(weight) >= 0.6
        if can_emit_observation:
            observation_export = {
                **accepted_observation,
                "export_record_id": f"{source_record_id}:observation:0",
                "source_record_id": source_record_id,
                "export_split": "accepted_records",
                "trust_tier": tier,
                "training_weight": weight,
                "inclusion_reason": "; ".join(reasons) if reasons else "observation fields accepted from reliable source",
                "excluded_fields": excluded_fields,
            }
            split_records["accepted_records"].append(observation_export)
        elif split == "audio_midi_only_records":
            observation_export = {
                **accepted_observation,
                "export_record_id": f"{source_record_id}:observation:0",
                "source_record_id": source_record_id,
                "export_split": "audio_midi_only_records",
                "trust_tier": tier,
                "training_weight": weight,
                "inclusion_reason": "; ".join(reasons) if reasons else "audio/midi context only",
                "excluded_fields": excluded_fields,
            }
            split_records["audio_midi_only_records"].append(observation_export)

        if str(record.get("label_status", "")) in {"weak_label", "heuristic_estimate", "interpretive_weak_label", "model_prediction"}:
            weak_export = {
                **weak_label_record,
                "export_record_id": f"{source_record_id}:weak_label:0",
                "source_record_id": source_record_id,
                "export_split": "weak_label_records",
                "trust_tier": tier,
                "training_weight": min(weight, 0.7),
                "inclusion_reason": "field-level weak label separated from accepted observations",
                "excluded_fields": [],
            }
            split_records["weak_label_records"].append(weak_export)

        if split == "review_required_records":
            review_export = {
                **review_record,
                "export_record_id": f"{source_record_id}:review:0",
                "source_record_id": source_record_id,
                "export_split": "review_required_records",
                "trust_tier": tier,
                "training_weight": min(weight, 0.4),
                "inclusion_reason": "; ".join(reasons) if reasons else "review required",
                "excluded_fields": [],
            }
            split_records["review_required_records"].append(review_export)

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
        "source_ai_record_count": len(ai_records),
        "accepted_observation_count": len(split_records["accepted_records"]),
        "weak_label_count": len(split_records["weak_label_records"]),
        "audio_midi_only_count": len(split_records["audio_midi_only_records"]),
        "review_required_count": len(split_records["review_required_records"]),
        "quarantined_count": len(split_records["quarantined_records"]),
        "field_trust_policy_version": POLICY_VERSION,
        "counts_per_split": {name: len(records) for name, records in split_records.items()},
        "inclusion_rules_used": {
            "accepted": "field-level observation subset derived from reliable source records.",
            "weak_label": "separate weak-label payloads with evidence/confidence metadata.",
            "audio_midi_only": "observation-only exports from reliable records without safe labels.",
            "review_required": "ambiguous/low-confidence/experimental records with review reasons.",
            "quarantined": "critical schema/provenance/time-range failures.",
        },
        "excluded_field_summary": excluded_field_summary,
        "limitations": [
            "Field-level splitting is heuristic and should be periodically recalibrated.",
            "Weak and interpretive labels remain non-ground-truth signals.",
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
