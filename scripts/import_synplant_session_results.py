from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
DATASET_PATH = ROOT_DIR / "datasets" / "synplant" / "session_results_v1.jsonl"
REPORT_JSON = ROOT_DIR / "reports" / "synplant" / "session_results_import_report.json"
REPORT_MD = ROOT_DIR / "reports" / "synplant" / "session_results_import_report.md"
ALLOWED_POLICIES = {
    "user_owned_training_candidate",
    "production_only_training_excluded",
    "splice_production_only",
    "unknown_blocked",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_row(row: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = [
        "session_id",
        "track_role",
        "seed_sample_id",
        "patch_ref",
        "rendered_audio_ref",
        "selected",
        "human_rating",
        "selection_reason",
        "training_allowed",
        "production_use_allowed",
        "source_policy_inherited",
    ]
    for key in required:
        if key not in row:
            errors.append(f"missing:{key}")
    policy = str(row.get("source_policy_inherited", ""))
    if policy not in ALLOWED_POLICIES:
        errors.append("invalid_source_policy_inherited")
    rating = row.get("human_rating")
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        errors.append("human_rating must be 1-5")
    if policy in {"production_only_training_excluded", "splice_production_only", "unknown_blocked"} and bool(
        row.get("training_allowed", False)
    ):
        errors.append("training_allowed must be false for restricted source policy")
    return errors


def import_synplant_session_results(path: Path) -> tuple[Path, Path, Path, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("results", [])
    if not isinstance(rows, list):
        raise ValueError("results must be a list")
    valid_rows: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            invalid.append({"index": idx, "errors": ["row_not_object"]})
            continue
        errors = _validate_row(row)
        if errors:
            invalid.append({"index": idx, "errors": errors})
            continue
        record = {
            "session_id": str(row["session_id"]),
            "track_role": str(row["track_role"]),
            "seed_sample_id": str(row["seed_sample_id"]),
            "patch_ref": str(row["patch_ref"]),
            "rendered_audio_ref": str(row["rendered_audio_ref"]),
            "selected": bool(row["selected"]),
            "human_rating": int(row["human_rating"]),
            "selection_reason": str(row["selection_reason"]),
            "training_allowed": bool(row["training_allowed"]),
            "production_use_allowed": bool(row["production_use_allowed"]),
            "source_policy_inherited": str(row["source_policy_inherited"]),
            "notes": str(row.get("notes", "")),
            "generation_method": "manual",
            "automation_claimed": False,
            "imported_at": now_iso(),
        }
        valid_rows.append(record)

    DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DATASET_PATH.open("a", encoding="utf-8") as handle:
        for row in valid_rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")

    report = {
        "status": "ok" if not invalid else "partial",
        "imported_rows": len(valid_rows),
        "invalid_rows": len(invalid),
        "invalid_details": invalid,
        "dataset_path": DATASET_PATH.resolve().relative_to(ROOT_DIR.resolve()).as_posix(),
        "automation_claimed": False,
        "created_at": now_iso(),
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    REPORT_MD.write_text(
        "\n".join(
            [
                "# Synplant Session Import Report",
                "",
                f"- status: `{report['status']}`",
                f"- imported_rows: `{report['imported_rows']}`",
                f"- invalid_rows: `{report['invalid_rows']}`",
                "- automation_claimed: `False`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return DATASET_PATH, REPORT_JSON, REPORT_MD, report


def main() -> int:
    parser = argparse.ArgumentParser(description="Import manual Synplant session results JSON.")
    parser.add_argument("session_results_json", help="Path to session results JSON")
    args = parser.parse_args()
    dataset_path, report_json, report_md, report = import_synplant_session_results(Path(args.session_results_json))
    print(f"SYNPLANT_SESSION_RESULTS_DATASET={dataset_path.as_posix()}")
    print(f"SYNPLANT_SESSION_RESULTS_REPORT_JSON={report_json.as_posix()}")
    print(f"SYNPLANT_SESSION_RESULTS_REPORT_MD={report_md.as_posix()}")
    print(f"SYNPLANT_SESSION_RESULTS_IMPORTED={report['imported_rows']}")
    print(f"SYNPLANT_SESSION_RESULTS_INVALID={report['invalid_rows']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
