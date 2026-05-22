from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.trust.failure_taxonomy import make_failure_record
from scripts.audit_training_dataset_record import audit_training_dataset_record
from scripts.benchmark_segments import benchmark_segments
from scripts.compute_transcription_reliability import compute_transcription_reliability
from scripts.evaluate_training_quality_gates import evaluate_training_quality_gates
from scripts.export_training_dataset_splits import export_training_dataset_splits
from scripts.extract_feature_pack import extract_feature_pack
from scripts.ingest_performance import ingest_performance
from scripts.process_performance import process_performance_manifest
from scripts.review_segments import review_segments
from scripts.summarize_training_exports import summarize_training_exports
from scripts.validate_feature_pack import validate_feature_pack
from scripts.validate_merged_midi import validate_merged_midi
from scripts.validate_training_export import validate_training_export

SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a"}


@dataclass
class BatchConfig:
    max_performances: int = 1
    max_windows: int = 3
    allow_full_completion: bool = False
    stop_on_failure: bool = True
    force_analysis: bool = False
    force_segmentation: bool = False
    force_feature_pack: bool = False
    force_export: bool = False
    allow_partial_export: bool = False


def _now_stamp() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")


def _discover_audio_files(inbox_folder: Path) -> list[Path]:
    if not inbox_folder.exists():
        return []
    return sorted(
        [
            path
            for path in inbox_folder.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS
        ]
    )


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _find_existing_manifest(source_path: Path, library_root: Path) -> Path | None:
    source_posix = source_path.resolve().as_posix()
    for candidate in library_root.glob("*/performance_manifest.json"):
        try:
            payload = _load_json(candidate)
        except Exception:  # noqa: BLE001
            continue
        if str(payload.get("source_path", "")) == source_posix:
            return candidate.resolve()
    return None


def _window_counts(segments_manifest_path: Path | None) -> dict[str, int]:
    counts = {"total_windows": 0, "successful_windows": 0, "failed_windows": 0, "remaining_windows": 0}
    if not segments_manifest_path or not segments_manifest_path.exists():
        return counts
    try:
        payload = _load_json(segments_manifest_path)
    except Exception:  # noqa: BLE001
        return counts
    windows = payload.get("transcription_windows", [])
    if not isinstance(windows, list):
        return counts
    total = len(windows)
    successful = sum(1 for item in windows if isinstance(item, dict) and str(item.get("status", "pending")) == "success")
    failed = sum(1 for item in windows if isinstance(item, dict) and str(item.get("status", "pending")) == "failed")
    counts["total_windows"] = total
    counts["successful_windows"] = successful
    counts["failed_windows"] = failed
    counts["remaining_windows"] = max(0, total - successful - failed)
    return counts


def _run_completed_pipeline(
    performance_manifest_path: Path,
    *,
    force_feature_pack: bool,
    force_export: bool,
) -> dict[str, Any]:
    payload = _load_json(performance_manifest_path)
    merged_midi_value = str(payload.get("active_merged_midi_path") or "").strip()
    merged_midi_path = Path(merged_midi_value) if merged_midi_value else None
    segments_manifest_value = str(payload.get("active_segments_manifest_path") or "").strip()
    if not segments_manifest_value:
        raise RuntimeError("active_segments_manifest_path missing after processing")
    segments_manifest_path = Path(segments_manifest_value)
    benchmark = benchmark_segments(segments_manifest_path)
    review_path = review_segments(segments_manifest_path)
    merged_validation = validate_merged_midi(merged_midi_path) if merged_midi_path and merged_midi_path.exists() else {}

    feature_dir = extract_feature_pack(performance_manifest_path) if force_feature_pack else extract_feature_pack(performance_manifest_path)
    feature_validation = validate_feature_pack(performance_manifest_path)
    if feature_validation.get("status") != "success":
        raise RuntimeError("feature pack validation failed")

    reliability_path = compute_transcription_reliability(performance_manifest_path)
    quality_path = evaluate_training_quality_gates(performance_manifest_path)
    audit_md_path, audit_json_path = audit_training_dataset_record(performance_manifest_path)
    export_dir = export_training_dataset_splits(performance_manifest_path) if force_export else export_training_dataset_splits(performance_manifest_path)
    export_validation = validate_training_export(export_dir)
    if export_validation.get("status") != "success":
        raise RuntimeError("training export validation failed")
    export_manifest = _load_json(export_dir / "export_manifest.json")
    return {
        "benchmark_summary": benchmark,
        "review_report_path": review_path.as_posix(),
        "merged_midi_validation": merged_validation,
        "feature_pack_dir": feature_dir.as_posix(),
        "feature_pack_validation": feature_validation,
        "transcription_reliability_path": reliability_path.as_posix(),
        "quality_gates_path": quality_path.as_posix(),
        "audit_md_path": audit_md_path.as_posix(),
        "audit_json_path": audit_json_path.as_posix(),
        "export_folder": export_dir.as_posix(),
        "export_validation": export_validation,
        "export_counts": {
            "accepted_observation_count": int(export_manifest.get("accepted_observation_count", 0) or 0),
            "weak_label_count": int(export_manifest.get("weak_label_count", 0) or 0),
            "review_required_count": int(export_manifest.get("review_required_count", 0) or 0),
            "quarantined_count": int(export_manifest.get("quarantined_count", 0) or 0),
        },
    }


def _result_md(result: dict[str, Any]) -> str:
    lines = [
        f"- performance_id: `{result.get('performance_id')}`",
        f"  - status: `{result.get('status')}`",
        f"  - source_audio: `{result.get('source_audio_path')}`",
        f"  - windows_before: `{json.dumps(result.get('windows_before', {}), ensure_ascii=True)}`",
        f"  - windows_after: `{json.dumps(result.get('windows_after', {}), ensure_ascii=True)}`",
    ]
    if result.get("export_folder"):
        lines.append(f"  - export_folder: `{result.get('export_folder')}`")
        lines.append(f"  - export_counts: `{json.dumps(result.get('export_counts', {}), ensure_ascii=True)}`")
    if result.get("failure_records"):
        lines.append(f"  - failure_records: `{json.dumps(result.get('failure_records'), ensure_ascii=True)}`")
    return "\n".join(lines)


def batch_trusted_exports(inbox_folder: Path, config: BatchConfig) -> dict[str, Any]:
    inbox_folder.mkdir(parents=True, exist_ok=True)
    library_root = Path("performances") / "library"
    library_root.mkdir(parents=True, exist_ok=True)
    reports_root = Path("reports") / "batches"
    reports_root.mkdir(parents=True, exist_ok=True)
    discovered = _discover_audio_files(inbox_folder)
    planned = discovered[: max(0, int(config.max_performances))]

    print(f"BATCH_FILES_FOUND={len(discovered)}")
    print(f"BATCH_PERFORMANCES_PLANNED={len(planned)}")
    print(f"BATCH_MAX_WINDOWS_PER_PERFORMANCE={config.max_windows}")
    print("BATCH_WILL_CALL_MODAL_OR_YOURMT3=yes")
    print(f"BATCH_ALLOW_FULL_COMPLETION={str(config.allow_full_completion).lower()}")
    print(f"BATCH_STOP_ON_FAILURE={str(config.stop_on_failure).lower()}")
    print(
        "BATCH_ESTIMATED_ACTIONS="
        f"ingest/reuse={len(planned)} process_cap={config.max_windows} "
        f"downstream_on_complete={str(config.allow_full_completion).lower()} or when already complete"
    )

    results: list[dict[str, Any]] = []
    ingested_count = 0
    total_windows_processed = 0
    total_successful_windows = 0
    total_failed_windows = 0
    total_accepted = 0
    total_weak = 0
    total_review = 0
    total_quarantine = 0
    completed_count = 0
    incomplete_count = 0
    failed_count = 0
    export_folders: list[str] = []

    for source_audio_path in planned:
        result: dict[str, Any] = {
            "source_audio_path": source_audio_path.resolve().as_posix(),
            "failure_records": [],
        }
        try:
            existing_manifest = _find_existing_manifest(source_audio_path, library_root)
            if existing_manifest is None:
                manifest_path = ingest_performance(source_audio_path)
                ingested_count += 1
            else:
                manifest_path = existing_manifest
            result["performance_manifest_path"] = manifest_path.resolve().as_posix()

            before_payload = _load_json(manifest_path)
            performance_id = str(before_payload.get("performance_id", "unknown_performance"))
            result["performance_id"] = performance_id
            before_segments = Path(str(before_payload.get("active_segments_manifest_path") or "")).resolve() if str(before_payload.get("active_segments_manifest_path") or "").strip() else None
            before_counts = _window_counts(before_segments)
            result["windows_before"] = before_counts
            remaining_before = int(before_counts.get("remaining_windows", 0))
            windows_budget = max(0, int(config.max_windows))
            conservative_blocked_completion = False
            if not config.allow_full_completion and remaining_before > 0 and remaining_before <= windows_budget:
                windows_budget = max(0, remaining_before - 1)
                conservative_blocked_completion = True
            result["windows_budget"] = windows_budget
            result["conservative_blocked_completion"] = conservative_blocked_completion

            if windows_budget > 0:
                process_performance_manifest(
                    manifest_path,
                    max_windows=windows_budget,
                    resume=True,
                    force_analysis=bool(config.force_analysis),
                    force_segmentation=bool(config.force_segmentation),
                )

            after_payload = _load_json(manifest_path)
            after_segments = Path(str(after_payload.get("active_segments_manifest_path") or "")).resolve() if str(after_payload.get("active_segments_manifest_path") or "").strip() else None
            after_counts = _window_counts(after_segments)
            result["windows_after"] = after_counts
            total_windows_processed += max(0, int(after_counts.get("successful_windows", 0)) - int(before_counts.get("successful_windows", 0)))
            total_successful_windows += int(after_counts.get("successful_windows", 0))
            total_failed_windows += int(after_counts.get("failed_windows", 0))
            remaining_after = int(after_counts.get("remaining_windows", 0))

            is_complete = remaining_after == 0
            if is_complete and (config.allow_full_completion or int(before_counts.get("remaining_windows", 0)) == 0):
                downstream = _run_completed_pipeline(
                    manifest_path,
                    force_feature_pack=bool(config.force_feature_pack),
                    force_export=bool(config.force_export),
                )
                result.update(downstream)
                result["status"] = "completed"
                completed_count += 1
                export_folder = str(result.get("export_folder", ""))
                if export_folder:
                    export_folders.append(export_folder)
                counts = result.get("export_counts", {}) if isinstance(result.get("export_counts"), dict) else {}
                total_accepted += int(counts.get("accepted_observation_count", 0) or 0)
                total_weak += int(counts.get("weak_label_count", 0) or 0)
                total_review += int(counts.get("review_required_count", 0) or 0)
                total_quarantine += int(counts.get("quarantined_count", 0) or 0)
            elif is_complete and not config.allow_full_completion:
                # Conservative mode: complete run is left resumable without downstream export.
                result["status"] = "incomplete_cap_reached"
                result["note"] = "conservative mode prevented full completion downstream steps"
                incomplete_count += 1
            elif config.allow_partial_export and int(after_counts.get("successful_windows", 0)) > 0:
                downstream = _run_completed_pipeline(
                    manifest_path,
                    force_feature_pack=bool(config.force_feature_pack),
                    force_export=bool(config.force_export),
                )
                result.update(downstream)
                result["status"] = "partial_export_completed"
                incomplete_count += 1
                export_folder = str(result.get("export_folder", ""))
                if export_folder:
                    export_folders.append(export_folder)
                counts = result.get("export_counts", {}) if isinstance(result.get("export_counts"), dict) else {}
                total_accepted += int(counts.get("accepted_observation_count", 0) or 0)
                total_weak += int(counts.get("weak_label_count", 0) or 0)
                total_review += int(counts.get("review_required_count", 0) or 0)
                total_quarantine += int(counts.get("quarantined_count", 0) or 0)
            else:
                result["status"] = "incomplete_cap_reached"
                incomplete_count += 1
        except Exception as exc:  # noqa: BLE001
            result["status"] = "failed"
            result["failure_records"] = [
                make_failure_record(
                    stage="batch_trusted_exports",
                    category="validation_failure",
                    severity="critical",
                    message=f"{exc.__class__.__name__}: {exc}",
                    artifact_path=result.get("performance_manifest_path"),
                    recoverable=True,
                    next_action="rerun with lower caps or inspect failing step logs",
                )
            ]
            failed_count += 1
            if config.stop_on_failure:
                results.append(result)
                break
        results.append(result)

    dataset_summary_json, dataset_summary_md = summarize_training_exports(Path("datasets") / "training_exports")
    summary_payload = {
        "files_discovered": len(discovered),
        "performances_ingested": ingested_count,
        "performances_processed": len(results),
        "completed_performances": completed_count,
        "incomplete_performances": incomplete_count,
        "failed_performances": failed_count,
        "windows_processed": total_windows_processed,
        "successful_windows": total_successful_windows,
        "failed_windows": total_failed_windows,
        "accepted_observation_count": total_accepted,
        "weak_label_count": total_weak,
        "review_required_count": total_review,
        "quarantined_count": total_quarantine,
        "export_folders": export_folders,
    }
    report = {
        "created_at": _now_stamp(),
        "inbox_folder": inbox_folder.resolve().as_posix(),
        "config": {
            "max_performances": config.max_performances,
            "max_windows": config.max_windows,
            "allow_full_completion": config.allow_full_completion,
            "stop_on_failure": config.stop_on_failure,
            "force_analysis": config.force_analysis,
            "force_segmentation": config.force_segmentation,
            "force_feature_pack": config.force_feature_pack,
            "force_export": config.force_export,
            "allow_partial_export": config.allow_partial_export,
        },
        "files_discovered": [path.resolve().as_posix() for path in discovered],
        "performances_planned": [path.resolve().as_posix() for path in planned],
        "performance_results": results,
        "summary": summary_payload,
        "dataset_summary_json_path": dataset_summary_json.as_posix(),
        "dataset_summary_md_path": dataset_summary_md.as_posix(),
    }
    stamp = _now_stamp()
    json_path = reports_root / f"{stamp}_batch_trusted_export_report.json"
    md_path = reports_root / f"{stamp}_batch_trusted_export_report.md"
    _save_json(json_path, report)
    md_lines = [
        f"# Batch Trusted Export Report ({stamp})",
        "",
        f"- inbox_folder: `{report['inbox_folder']}`",
        f"- files_discovered: `{len(discovered)}`",
        f"- performances_planned: `{len(planned)}`",
        f"- performances_processed: `{summary_payload['performances_processed']}`",
        f"- completed_performances: `{summary_payload['completed_performances']}`",
        f"- incomplete_performances: `{summary_payload['incomplete_performances']}`",
        f"- failed_performances: `{summary_payload['failed_performances']}`",
        f"- windows_processed: `{summary_payload['windows_processed']}`",
        f"- successful_windows: `{summary_payload['successful_windows']}`",
        f"- failed_windows: `{summary_payload['failed_windows']}`",
        f"- accepted_observation_count: `{summary_payload['accepted_observation_count']}`",
        f"- weak_label_count: `{summary_payload['weak_label_count']}`",
        f"- review_required_count: `{summary_payload['review_required_count']}`",
        f"- quarantined_count: `{summary_payload['quarantined_count']}`",
        f"- dataset_summary_json_path: `{report['dataset_summary_json_path']}`",
        f"- dataset_summary_md_path: `{report['dataset_summary_md_path']}`",
        "",
        "## Performance Results",
    ]
    if results:
        md_lines.extend(_result_md(item) for item in results)
    else:
        md_lines.append("- inbox empty; batch workflow ready.")
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    if not discovered:
        print("inbox empty; batch workflow ready.")
    print(f"BATCH_TRUSTED_REPORT_JSON={json_path.as_posix()}")
    print(f"BATCH_TRUSTED_REPORT_MD={md_path.as_posix()}")
    print(f"DATASET_SUMMARY_JSON={dataset_summary_json.as_posix()}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run safe, capped trusted-export workflow for inbox audio files.")
    parser.add_argument("inbox_folder", nargs="?", default="performances/inbox")
    parser.add_argument("--max-performances", type=int, default=1)
    parser.add_argument("--max-windows", type=int, default=3)
    parser.add_argument("--allow-full-completion", action="store_true")
    parser.add_argument("--stop-on-failure", action="store_true", default=True)
    parser.add_argument("--force-analysis", action="store_true")
    parser.add_argument("--force-segmentation", action="store_true")
    parser.add_argument("--force-feature-pack", action="store_true")
    parser.add_argument("--force-export", action="store_true")
    parser.add_argument("--allow-partial-export", action="store_true")
    args = parser.parse_args()
    config = BatchConfig(
        max_performances=max(0, int(args.max_performances)),
        max_windows=max(0, int(args.max_windows)),
        allow_full_completion=bool(args.allow_full_completion),
        stop_on_failure=bool(args.stop_on_failure),
        force_analysis=bool(args.force_analysis),
        force_segmentation=bool(args.force_segmentation),
        force_feature_pack=bool(args.force_feature_pack),
        force_export=bool(args.force_export),
        allow_partial_export=bool(args.allow_partial_export),
    )
    batch_trusted_exports(Path(args.inbox_folder), config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
