from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.feature_dataset_common import load_json, now_iso, save_json
from scripts.trust_common import load_jsonl_records, resolve_performance_context, trust_dir


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = load_json(path)
    return payload if isinstance(payload, dict) else {}


def _label_counts(ai_records: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in ai_records:
        status = str(record.get("label_status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
    return counts


def audit_training_dataset_record(performance_manifest_path: Path) -> tuple[Path, Path]:
    ctx = resolve_performance_context(performance_manifest_path)
    feature_dir = ctx["feature_dir"]
    trust_output_dir = trust_dir(feature_dir)

    rhythm_path = feature_dir / "rhythm_features.json"
    harmony_path = feature_dir / "harmony_features.json"
    tags_path = feature_dir / "tags.json"
    ai_path = feature_dir / "ai_training_records.jsonl"
    manifest_path = feature_dir / "feature_pack_manifest.json"
    merge_report_path = ctx["segments_manifest_path"].parent / "merged" / "merge_report.json"
    reliability_path = trust_output_dir / "transcription_reliability.json"
    quality_path = trust_output_dir / "quality_gates.json"
    external_dir = feature_dir / "external_model_features"

    rhythm_payload = _read_json_if_exists(rhythm_path)
    harmony_payload = _read_json_if_exists(harmony_path)
    tags_payload = _read_json_if_exists(tags_path)
    ai_records = load_jsonl_records(ai_path)
    reliability_payload = _read_json_if_exists(reliability_path)
    quality_payload = _read_json_if_exists(quality_path)

    quality_status = str(quality_payload.get("overall_quality_status", "review_required"))
    inclusion_decision = quality_status
    recommended_split = str(quality_payload.get("recommended_dataset_split", "review"))

    strong_usable = [
        "MIDI note events and transcription window timing",
        "Merged MIDI artifact (if present) and stitch diagnostics",
        "Raw rhythm density and velocity statistics",
        "Pitch-class histograms and transcription statuses",
    ]
    weak_usable = [
        "Chord label candidates",
        "Rhythm/chord region candidates",
        "Motif and rhythm-family candidates",
        "Ontology/semantic interpretation tags",
    ]
    experimental = [
        "Rhythm-family classifications without strong calibration support",
        "Philosophical rhythm concept labels",
        "Syncopation and groove proxy inferences",
        "Motif ranking/importance heuristics",
    ]

    missing_data: list[str] = []
    if not (external_dir / "essentia_features.json").exists():
        missing_data.append("Essentia descriptors")
    if not (external_dir / "musicnn_features.json").exists():
        missing_data.append("musicnn semantic tags")
    if not (external_dir / "feature_consensus.json").exists():
        missing_data.append("external model consensus")
    if not any(str(record.get("verification_status", "unverified")) == "human_verified" for record in ai_records):
        missing_data.append("human verification labels")
    if not (external_dir / "beat_tracker_features.json").exists():
        missing_data.append("beat/downbeat external witness")

    reliability_summary = reliability_payload.get("summary", {}) if isinstance(reliability_payload.get("summary"), dict) else {}
    label_status_counts = _label_counts(ai_records)

    audit_json = {
        "performance_id": ctx["performance_id"],
        "segment_run_id": ctx["segment_run_id"],
        "created_at": now_iso(),
        "artifacts": {
            "source_audio_reference": str(ctx["performance_manifest"].get("source_path")),
            "active_analysis_path": str(ctx["analysis_path"]) if ctx["analysis_path"] else None,
            "active_segments_manifest": ctx["segments_manifest_path"].as_posix(),
            "window_midi_count": int(reliability_summary.get("window_count", 0) or 0),
            "merged_midi_path": str(ctx["merged_midi_path"]) if ctx["merged_midi_path"] else None,
            "merge_report_path": merge_report_path.resolve().as_posix() if merge_report_path.exists() else None,
            "feature_pack_files": {
                "rhythm_features": rhythm_path.resolve().as_posix() if rhythm_path.exists() else None,
                "harmony_features": harmony_path.resolve().as_posix() if harmony_path.exists() else None,
                "tags": tags_path.resolve().as_posix() if tags_path.exists() else None,
                "feature_pack_manifest": manifest_path.resolve().as_posix() if manifest_path.exists() else None,
            },
            "ai_jsonl_path": ai_path.resolve().as_posix() if ai_path.exists() else None,
        },
        "strongly_usable_data": strong_usable,
        "usable_as_weak_labels": weak_usable,
        "experimental_low_confidence_data": experimental,
        "missing_data": missing_data,
        "ai_readiness_assessment": {
            "ai_jsonl_usable": ai_path.exists() and len(ai_records) > 0,
            "safe_for_training_now": [
                "raw_observation and derived_observation records",
                "high/medium reliability windows",
                "records with complete provenance fields",
            ],
            "weak_labels_only": [
                "heuristic_estimate records",
                "weak_label and interpretive_weak_label records",
            ],
            "exclude_or_downweight": [
                "failed/missing reliability windows",
                "review_required records",
                "ambiguous labels without corroboration",
            ],
            "label_status_counts": label_status_counts,
            "reliability_summary": reliability_summary,
        },
        "dataset_inclusion_decision": inclusion_decision,
        "recommended_dataset_split": recommended_split,
        "recommended_next_steps": [
            "Collect human verification for high-impact weak labels.",
            "Use accepted/audio_midi_only splits for baseline training first.",
            "Review quarantined/review records before inclusion.",
        ],
    }

    audit_json_path = trust_output_dir / "training_data_audit.json"
    save_json(audit_json_path, audit_json)

    report_dir = Path("reports") / "data_audits"
    report_dir.mkdir(parents=True, exist_ok=True)
    audit_md_path = report_dir / f"{ctx['performance_id']}_training_data_audit.md"
    lines = [
        f"# Training Data Audit - {ctx['performance_id']}",
        "",
        "## 1. Artifacts generated",
        f"- source audio reference: `{audit_json['artifacts']['source_audio_reference']}`",
        f"- active analysis path: `{audit_json['artifacts']['active_analysis_path']}`",
        f"- active segments manifest: `{audit_json['artifacts']['active_segments_manifest']}`",
        f"- window MIDI count: `{audit_json['artifacts']['window_midi_count']}`",
        f"- merged MIDI path: `{audit_json['artifacts']['merged_midi_path']}`",
        f"- merge report path: `{audit_json['artifacts']['merge_report_path']}`",
        f"- feature pack files: `{json.dumps(audit_json['artifacts']['feature_pack_files'], ensure_ascii=True)}`",
        f"- AI JSONL path: `{audit_json['artifacts']['ai_jsonl_path']}`",
        "",
        "## 2. Strongly usable data",
    ]
    lines.extend(f"- {item}" for item in strong_usable)
    lines.extend(["", "## 3. Usable as weak labels"])
    lines.extend(f"- {item}" for item in weak_usable)
    lines.extend(["", "## 4. Experimental / low-confidence data"])
    lines.extend(f"- {item}" for item in experimental)
    lines.extend(["", "## 5. Missing data"])
    if missing_data:
        lines.extend(f"- {item}" for item in missing_data)
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## 6. AI-readiness assessment",
            f"- Is ai_training_records.jsonl usable? `{audit_json['ai_readiness_assessment']['ai_jsonl_usable']}`",
            f"- Safe for training now: `{json.dumps(audit_json['ai_readiness_assessment']['safe_for_training_now'], ensure_ascii=True)}`",
            f"- Weak labels only: `{json.dumps(audit_json['ai_readiness_assessment']['weak_labels_only'], ensure_ascii=True)}`",
            f"- Exclude/downweight: `{json.dumps(audit_json['ai_readiness_assessment']['exclude_or_downweight'], ensure_ascii=True)}`",
            "",
            "## 7. Dataset inclusion decision",
            f"- decision: `{inclusion_decision}`",
            f"- recommended split: `{recommended_split}`",
            "",
            "## 8. Recommended next steps",
        ]
    )
    lines.extend(f"- {item}" for item in audit_json["recommended_next_steps"])
    audit_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return audit_md_path.resolve(), audit_json_path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit one performance for training-data trust/readiness.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    args = parser.parse_args()
    md_path, json_path = audit_training_dataset_record(Path(args.performance_manifest))
    print(f"TRAINING_AUDIT_MD_PATH={md_path.as_posix()}")
    print(f"TRAINING_AUDIT_JSON_PATH={json_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
