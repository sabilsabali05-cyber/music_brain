from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATASET_PATH = ROOT_DIR / "datasets" / "synplant" / "session_results_v1.jsonl"
REPORT_JSON = ROOT_DIR / "reports" / "synplant" / "synplant_sessions_validation_report.json"
REPORT_MD = ROOT_DIR / "reports" / "synplant" / "synplant_sessions_validation_report.md"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_synplant_sessions() -> tuple[Path, Path, dict]:
    errors: list[str] = []
    rows = 0
    selected_count = 0
    training_allowed_count = 0
    if DATASET_PATH.exists():
        with DATASET_PATH.open("r", encoding="utf-8") as handle:
            for idx, line in enumerate(handle):
                line = line.strip()
                if not line:
                    continue
                rows += 1
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    errors.append(f"row_{idx}:invalid_json")
                    continue
                policy = str(payload.get("source_policy_inherited", ""))
                training_allowed = bool(payload.get("training_allowed", False))
                if bool(payload.get("selected", False)):
                    selected_count += 1
                if training_allowed:
                    training_allowed_count += 1
                if policy in {"production_only_training_excluded", "splice_production_only", "unknown_blocked"} and training_allowed:
                    errors.append(f"row_{idx}:training_allowed_conflicts_with_policy")
                rating = payload.get("human_rating")
                if not isinstance(rating, int) or rating < 1 or rating > 5:
                    errors.append(f"row_{idx}:invalid_human_rating")
                if payload.get("automation_claimed") is True:
                    errors.append(f"row_{idx}:automation_claim_not_allowed")

    report = {
        "status": "ok" if not errors else "invalid",
        "dataset_exists": DATASET_PATH.exists(),
        "row_count": rows,
        "selected_count": selected_count,
        "training_allowed_count": training_allowed_count,
        "errors": errors,
        "automation_claimed": False,
        "created_at": now_iso(),
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    REPORT_MD.write_text(
        "\n".join(
            [
                "# Synplant Sessions Validation Report",
                "",
                f"- status: `{report['status']}`",
                f"- dataset_exists: `{report['dataset_exists']}`",
                f"- row_count: `{report['row_count']}`",
                f"- selected_count: `{report['selected_count']}`",
                f"- training_allowed_count: `{report['training_allowed_count']}`",
                f"- errors: `{len(errors)}`",
                "- automation_claimed: `False`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return REPORT_JSON, REPORT_MD, report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate imported Synplant session logs/results.")
    parser.parse_args()
    report_json, report_md, report = validate_synplant_sessions()
    print(f"SYNPLANT_VALIDATION_REPORT_JSON={report_json.as_posix()}")
    print(f"SYNPLANT_VALIDATION_REPORT_MD={report_md.as_posix()}")
    print(f"SYNPLANT_VALIDATION_STATUS={report['status']}")
    print(f"SYNPLANT_VALIDATION_ERRORS={len(report['errors'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
