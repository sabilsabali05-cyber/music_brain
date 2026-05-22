from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.validate_training_export import validate_training_export


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("batch report must be a JSON object")
    return payload


def _require_non_negative_int(container: dict[str, Any], field: str, errors: list[str], *, prefix: str) -> int:
    value = container.get(field, 0)
    try:
        parsed = int(value)
    except Exception:  # noqa: BLE001
        errors.append(f"{prefix} field is not int-like: {field}")
        return 0
    if parsed < 0:
        errors.append(f"{prefix} count is negative: {field}")
    return parsed


def validate_batch_report(report_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    if not report_path.exists():
        return {"status": "failed", "errors": [f"missing report: {report_path.as_posix()}"]}
    try:
        payload = _load_json(report_path)
    except Exception as exc:  # noqa: BLE001
        return {"status": "failed", "errors": [f"report parse error: {exc}"]}

    required_top_level = [
        "created_at",
        "inbox_folder",
        "config",
        "files_discovered",
        "performances_planned",
        "performance_results",
        "summary",
        "dataset_summary_json_path",
        "dataset_summary_md_path",
    ]
    for field in required_top_level:
        if field not in payload:
            errors.append(f"missing top-level field: {field}")

    summary = payload.get("summary", {})
    if not isinstance(summary, dict):
        errors.append("summary must be an object")
        summary = {}
    common_summary_count_fields = [
        "files_discovered",
        "performances_ingested",
        "performances_processed",
        "completed_performances",
        "incomplete_performances",
        "failed_performances",
        "accepted_observation_count",
        "weak_label_count",
        "review_required_count",
        "quarantined_count",
    ]
    for field in common_summary_count_fields:
        _require_non_negative_int(summary, field, errors, prefix="summary")

    has_new_summary_metrics = all(
        field in summary
        for field in (
            "windows_total_after",
            "successful_windows_after",
            "failed_windows_after",
            "remaining_windows_after",
            "newly_successful_windows",
            "newly_failed_windows",
            "windows_processed_this_run",
        )
    )
    has_legacy_summary_metrics = all(
        field in summary for field in ("windows_processed", "successful_windows", "failed_windows")
    )

    performance_results = payload.get("performance_results", [])
    if not isinstance(performance_results, list):
        errors.append("performance_results must be a list")
        performance_results = []
    if has_new_summary_metrics:
        summary_fields = (
            "windows_total_after",
            "successful_windows_after",
            "failed_windows_after",
            "remaining_windows_after",
            "newly_successful_windows",
            "newly_failed_windows",
            "windows_processed_this_run",
        )
        for field in summary_fields:
            _require_non_negative_int(summary, field, errors, prefix="summary")

        per_perf_required_fields = (
            "windows_total_before",
            "successful_windows_before",
            "failed_windows_before",
            "remaining_windows_before",
            "windows_total_after",
            "successful_windows_after",
            "failed_windows_after",
            "remaining_windows_after",
            "newly_successful_windows",
            "newly_failed_windows",
            "windows_processed_this_run",
        )
        per_perf_sums = {field: 0 for field in summary_fields}
        for index, item in enumerate(performance_results):
            if not isinstance(item, dict):
                continue
            prefix = f"performance_results[{index}]"
            for field in per_perf_required_fields:
                if field not in item:
                    errors.append(f"{prefix} missing field: {field}")
            for field in per_perf_required_fields:
                _require_non_negative_int(item, field, errors, prefix=prefix)

            successful_before = _require_non_negative_int(item, "successful_windows_before", errors, prefix=prefix)
            successful_after = _require_non_negative_int(item, "successful_windows_after", errors, prefix=prefix)
            failed_before = _require_non_negative_int(item, "failed_windows_before", errors, prefix=prefix)
            failed_after = _require_non_negative_int(item, "failed_windows_after", errors, prefix=prefix)
            newly_successful = _require_non_negative_int(item, "newly_successful_windows", errors, prefix=prefix)
            newly_failed = _require_non_negative_int(item, "newly_failed_windows", errors, prefix=prefix)
            processed_this_run = _require_non_negative_int(item, "windows_processed_this_run", errors, prefix=prefix)

            if newly_successful != successful_after - successful_before:
                errors.append(
                    f"{prefix} newly_successful_windows mismatch: {newly_successful} != "
                    f"{successful_after} - {successful_before}"
                )
            if newly_failed != failed_after - failed_before:
                errors.append(f"{prefix} newly_failed_windows mismatch: {newly_failed} != {failed_after} - {failed_before}")
            if processed_this_run != newly_successful + newly_failed:
                errors.append(
                    f"{prefix} windows_processed_this_run mismatch: {processed_this_run} != "
                    f"{newly_successful} + {newly_failed}"
                )
            for field in summary_fields:
                per_perf_sums[field] += _require_non_negative_int(item, field, errors, prefix=prefix)

        for field in summary_fields:
            summary_value = _require_non_negative_int(summary, field, errors, prefix="summary")
            if summary_value != per_perf_sums[field]:
                errors.append(
                    f"summary {field} mismatch: {summary_value} != "
                    f"per-performance total {per_perf_sums[field]}"
                )
        summary_newly_successful = _require_non_negative_int(summary, "newly_successful_windows", errors, prefix="summary")
        summary_newly_failed = _require_non_negative_int(summary, "newly_failed_windows", errors, prefix="summary")
        summary_processed = _require_non_negative_int(summary, "windows_processed_this_run", errors, prefix="summary")
        if summary_processed != summary_newly_successful + summary_newly_failed:
            errors.append(
                "summary windows_processed_this_run mismatch: "
                f"{summary_processed} != {summary_newly_successful} + {summary_newly_failed}"
            )
    elif has_legacy_summary_metrics:
        for field in ("windows_processed", "successful_windows", "failed_windows"):
            _require_non_negative_int(summary, field, errors, prefix="summary")

    for item in performance_results:
        if not isinstance(item, dict):
            errors.append("performance_results entries must be objects")
            continue
        status = str(item.get("status", "unknown"))
        export_folder = str(item.get("export_folder", "") or "")
        if status == "completed":
            if not export_folder:
                errors.append("completed performance missing export_folder")
                continue
            path = Path(export_folder)
            if not path.exists():
                errors.append(f"completed export folder missing: {export_folder}")
            else:
                export_validation = validate_training_export(path)
                if export_validation.get("status") != "success":
                    errors.append(f"completed export folder failed validation: {export_folder}")
        if status == "failed":
            failure_records = item.get("failure_records")
            if not isinstance(failure_records, list) or not failure_records:
                errors.append("failed performance missing failure taxonomy records")

    return {
        "status": "success" if not errors else "failed",
        "report_path": report_path.resolve().as_posix(),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate batch trusted-export report JSON.")
    parser.add_argument("batch_report_json", help="Path to batch report JSON")
    args = parser.parse_args()
    summary = validate_batch_report(Path(args.batch_report_json))
    print("BATCH_REPORT_VALIDATION=" + json.dumps(summary, ensure_ascii=True))
    return 0 if summary.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
