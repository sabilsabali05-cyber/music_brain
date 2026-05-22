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
    count_fields = [
        "files_discovered",
        "performances_ingested",
        "performances_processed",
        "completed_performances",
        "incomplete_performances",
        "failed_performances",
        "windows_processed",
        "successful_windows",
        "failed_windows",
        "accepted_observation_count",
        "weak_label_count",
        "review_required_count",
        "quarantined_count",
    ]
    for field in count_fields:
        value = summary.get(field, 0)
        try:
            parsed = int(value)
        except Exception:  # noqa: BLE001
            errors.append(f"summary field is not int-like: {field}")
            continue
        if parsed < 0:
            errors.append(f"summary count is negative: {field}")

    performance_results = payload.get("performance_results", [])
    if not isinstance(performance_results, list):
        errors.append("performance_results must be a list")
        performance_results = []
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
