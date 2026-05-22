from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.trust.failure_taxonomy import make_failure_record
from scripts.feature_dataset_common import load_json, now_iso, save_json, summarize_window_counts
from scripts.trust_common import load_jsonl_records, resolve_performance_context, trust_dir
from scripts.validate_feature_pack import validate_feature_pack


def _gate(
    gate_name: str,
    status: str,
    severity: str,
    evidence: dict[str, Any],
    recommendation: str,
) -> dict[str, Any]:
    return {
        "gate_name": gate_name,
        "status": status,
        "severity": severity,
        "evidence": evidence,
        "recommendation": recommendation,
    }


def evaluate_training_quality_gates(performance_manifest_path: Path) -> Path:
    ctx = resolve_performance_context(performance_manifest_path)
    manifest = ctx["performance_manifest"]
    segments_manifest = load_json(ctx["segments_manifest_path"])
    windows_summary = summarize_window_counts(segments_manifest)

    gates: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    source_path = str(manifest.get("source_path") or "").strip()
    source_exists = bool(source_path and Path(source_path).exists())
    gates.append(
        _gate(
            "source_file_exists",
            "pass" if source_exists else "fail",
            "critical" if not source_exists else "info",
            {"source_path": source_path},
            "Provide a valid local source_path in performance_manifest." if not source_exists else "Source path present.",
        )
    )
    if not source_exists:
        failures.append(make_failure_record("source", "source_failure", "critical", "Source file missing.", artifact_path=source_path))

    duration_known = manifest.get("duration_seconds") is not None
    gates.append(
        _gate(
            "source_duration_known",
            "pass" if duration_known else "warn",
            "warning" if not duration_known else "info",
            {"duration_seconds": manifest.get("duration_seconds")},
            "Populate duration_seconds to support reliable density metrics.",
        )
    )

    checksum = manifest.get("source_sha256") or manifest.get("source_checksum") or manifest.get("checksum")
    gates.append(
        _gate(
            "source_checksum_exists",
            "pass" if checksum else "warn",
            "warning" if not checksum else "info",
            {"checksum": checksum},
            "Add source checksum for provenance tracking.",
        )
    )
    if not checksum:
        failures.append(
            make_failure_record(
                "source",
                "provenance_failure",
                "warning",
                "Source checksum missing.",
                artifact_path=source_path,
                next_action="Persist source SHA-256 checksum in performance manifest.",
            )
        )

    decode_check = "pass" if source_exists else "not_applicable"
    gates.append(
        _gate(
            "source_decodes_checkable",
            decode_check,
            "info" if source_exists else "warning",
            {"check": "file existence and non-zero size proxy"},
            "Run deeper decode validation in future with dedicated decoder checks.",
        )
    )

    analysis_exists = bool(ctx["analysis_path"] and Path(ctx["analysis_path"]).exists())
    gates.append(
        _gate(
            "active_analysis_path_exists",
            "pass" if analysis_exists else "warn",
            "warning" if not analysis_exists else "info",
            {"active_analysis_path": str(ctx["analysis_path"]) if ctx["analysis_path"] else None},
            "Re-run analysis stage if this path is expected for current run.",
        )
    )
    if not analysis_exists:
        failures.append(make_failure_record("analysis", "analysis_failure", "warning", "Active analysis path missing."))

    segments_exists = ctx["segments_manifest_path"].exists()
    gates.append(
        _gate(
            "active_segments_manifest_exists",
            "pass" if segments_exists else "fail",
            "critical" if not segments_exists else "info",
            {"active_segments_manifest_path": ctx["segments_manifest_path"].as_posix()},
            "Set active_segments_manifest_path to a valid run manifest.",
        )
    )
    if not segments_exists:
        failures.append(
            make_failure_record(
                "segmentation",
                "segmentation_failure",
                "critical",
                "Active segments manifest missing.",
                artifact_path=ctx["segments_manifest_path"].as_posix(),
            )
        )

    successful_windows = int(windows_summary.get("successful", 0))
    gates.append(
        _gate(
            "successful_transcription_window_exists",
            "pass" if successful_windows > 0 else "fail",
            "critical" if successful_windows == 0 else "info",
            {"successful_windows": successful_windows, "windows_summary": windows_summary},
            "Ensure at least one successful transcription window before dataset export.",
        )
    )
    if successful_windows == 0:
        failures.append(make_failure_record("transcription", "transcription_failure", "critical", "No successful transcription windows."))

    performance_complete = int(windows_summary.get("remaining", 0)) == 0
    merged_exists = bool(ctx["merged_midi_path"] and Path(ctx["merged_midi_path"]).exists())
    merged_status = "pass" if (not performance_complete or merged_exists) else "warn"
    gates.append(
        _gate(
            "merged_midi_exists_if_complete",
            merged_status,
            "warning" if merged_status != "pass" else "info",
            {"performance_complete": performance_complete, "merged_midi_path": str(ctx["merged_midi_path"]) if ctx["merged_midi_path"] else None},
            "Run stitch-midi for complete performances to improve global feature consistency.",
        )
    )

    feature_dir = ctx["feature_dir"]
    feature_pack_exists = feature_dir.exists()
    gates.append(
        _gate(
            "feature_pack_exists",
            "pass" if feature_pack_exists else "fail",
            "critical" if not feature_pack_exists else "info",
            {"feature_pack_dir": feature_dir.as_posix()},
            "Run extract-feature-pack before trust evaluation.",
        )
    )
    if not feature_pack_exists:
        failures.append(make_failure_record("feature_pack", "validation_failure", "critical", "Feature pack directory missing."))

    validation_summary = validate_feature_pack(performance_manifest_path) if feature_pack_exists else {"status": "failed", "warnings": ["feature pack missing"]}
    validation_ok = validation_summary.get("status") == "success"
    gates.append(
        _gate(
            "feature_pack_validates",
            "pass" if validation_ok else "fail",
            "critical" if not validation_ok else "info",
            {"validation_status": validation_summary.get("status"), "warnings": validation_summary.get("warnings", [])},
            "Resolve feature pack validation warnings/errors before export.",
        )
    )
    if not validation_ok:
        failures.append(make_failure_record("validation", "validation_failure", "critical", "Feature pack validation failed."))

    ai_jsonl_path = feature_dir / "ai_training_records.jsonl"
    ai_records = load_jsonl_records(ai_jsonl_path)
    gates.append(
        _gate(
            "ai_jsonl_exists",
            "pass" if ai_jsonl_path.exists() else "fail",
            "critical" if not ai_jsonl_path.exists() else "info",
            {"ai_training_records_path": ai_jsonl_path.as_posix(), "record_count": len(ai_records)},
            "Build AI training records JSONL before audit/export.",
        )
    )

    tags_path = feature_dir / "tags.json"
    tags_payload = load_json(tags_path) if tags_path.exists() else {}
    tags = tags_payload.get("tags", []) if isinstance(tags_payload.get("tags"), list) else []
    tags_have_evidence = all(isinstance(item, dict) and "evidence" in item for item in tags) if tags else False
    gates.append(
        _gate(
            "tags_have_evidence",
            "pass" if tags_have_evidence else ("warn" if tags else "fail"),
            "warning" if tags_have_evidence is False else "info",
            {"tag_count": len(tags), "tags_have_evidence": tags_have_evidence},
            "Ensure tag records include evidence payloads.",
        )
    )

    confidence_fields_exist = True
    provenance_fields_exist = True
    for record in ai_records[:200]:
        if "confidence" not in record:
            confidence_fields_exist = False
        if "source_artifact_paths" not in record or "feature_version" not in record:
            provenance_fields_exist = False
    gates.append(
        _gate(
            "ai_confidence_fields_exist",
            "pass" if confidence_fields_exist else "warn",
            "warning" if not confidence_fields_exist else "info",
            {"record_count_checked": min(200, len(ai_records))},
            "Backfill confidence on all AI records.",
        )
    )
    gates.append(
        _gate(
            "ai_provenance_fields_exist",
            "pass" if provenance_fields_exist else "warn",
            "warning" if not provenance_fields_exist else "info",
            {"record_count_checked": min(200, len(ai_records))},
            "Backfill source_artifact_paths and feature_version fields.",
        )
    )

    critical_fail = any(gate["status"] == "fail" and gate["severity"] == "critical" for gate in gates)
    fail_count = sum(1 for gate in gates if gate["status"] == "fail")
    warn_count = sum(1 for gate in gates if gate["status"] == "warn")
    if critical_fail:
        overall_quality_status = "quarantined"
        recommended_dataset_split = "quarantine"
    elif fail_count > 0:
        overall_quality_status = "review_required"
        recommended_dataset_split = "review"
    elif warn_count > 0:
        overall_quality_status = "weak_accept"
        recommended_dataset_split = "weak_labels"
    else:
        overall_quality_status = "accepted"
        recommended_dataset_split = "train"

    payload = {
        "performance_id": ctx["performance_id"],
        "segment_run_id": ctx["segment_run_id"],
        "created_at": now_iso(),
        "gates": gates,
        "failure_records": failures,
        "summary": {
            "total_gates": len(gates),
            "pass_count": sum(1 for gate in gates if gate["status"] == "pass"),
            "warn_count": warn_count,
            "fail_count": fail_count,
            "critical_fail": critical_fail,
        },
        "overall_quality_status": overall_quality_status,
        "recommended_dataset_split": recommended_dataset_split,
    }
    output_path = trust_dir(feature_dir) / "quality_gates.json"
    save_json(output_path, payload)
    return output_path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate training quality gates for a performance run.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    args = parser.parse_args()
    output_path = evaluate_training_quality_gates(Path(args.performance_manifest))
    print(f"QUALITY_GATES_PATH={output_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
