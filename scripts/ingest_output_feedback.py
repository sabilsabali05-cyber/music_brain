from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.taste_learning.taste_feedback_schema import CORE_TASTE_LABELS, validate_taste_feedback  # noqa: E402


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT_DIR.resolve()).as_posix()
    except Exception:  # noqa: BLE001
        return path.as_posix()


def _read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        return []
    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return []
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            return [payload]
        return []
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest reviewed output feedback into authorized taste-learning dataset.")
    parser.add_argument("--input", default="reports/review_queue/music_understanding_loop_feedback.json")
    args = parser.parse_args()
    input_path = ROOT_DIR / args.input
    out_path = ROOT_DIR / "datasets" / "taste_learning" / "taste_feedback.jsonl"
    report_json = ROOT_DIR / "reports" / "taste_learning" / "feedback_ingestion_report.json"
    report_md = ROOT_DIR / "reports" / "taste_learning" / "feedback_ingestion_report.md"

    rows = _read_rows(input_path)
    accepted: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for row in rows:
        ok, reason = validate_taste_feedback(row)
        normalized = dict(row)
        if str(normalized.get("taste_label", "")).strip().lower() not in CORE_TASTE_LABELS:
            normalized["taste_label"] = "neutral"
            ok = False
            reason = "invalid_taste_label"
        if ok:
            accepted.append(normalized)
        else:
            normalized["blocked_reason"] = reason
            blocked.append(normalized)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    if accepted:
        with out_path.open("a", encoding="utf-8") as handle:
            for row in accepted:
                handle.write(json.dumps(row, ensure_ascii=True) + "\n")

    payload = {
        "input_path": _repo_rel(input_path),
        "accepted_count": len(accepted),
        "blocked_count": len(blocked),
        "blocked_reasons": sorted({row.get("blocked_reason", "unknown") for row in blocked}),
        "dataset_path": _repo_rel(out_path),
        "policy": {
            "authorized_data_only": True,
            "no_private_path_expansion": True,
        },
    }
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    report_md.write_text(
        "\n".join(
            [
                "# Feedback Ingestion Report",
                "",
                f"- input_path: `{payload['input_path']}`",
                f"- accepted_count: `{payload['accepted_count']}`",
                f"- blocked_count: `{payload['blocked_count']}`",
                f"- blocked_reasons: `{', '.join(payload['blocked_reasons']) if payload['blocked_reasons'] else 'none'}`",
                f"- dataset_path: `{payload['dataset_path']}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"FEEDBACK_ACCEPTED_COUNT={payload['accepted_count']}")
    print(f"FEEDBACK_BLOCKED_COUNT={payload['blocked_count']}")
    print(f"TASTE_FEEDBACK_DATASET={_repo_rel(out_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
