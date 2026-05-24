from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
NORMALIZED_INPUT = ROOT_DIR / "datasets" / "normalized_music_corpus" / "normalized_music_corpus.jsonl"
TRAIN_PATH = ROOT_DIR / "datasets" / "training_corpus" / "train.jsonl"
VALIDATION_PATH = ROOT_DIR / "datasets" / "training_corpus" / "validation.jsonl"
RETRIEVAL_ONLY_PATH = ROOT_DIR / "datasets" / "training_corpus" / "retrieval_only.jsonl"
REVIEW_REQUIRED_PATH = ROOT_DIR / "datasets" / "training_corpus" / "review_required.jsonl"
REPORT_JSON = ROOT_DIR / "reports" / "training_corpus" / "corpus_split_report.json"
REPORT_MD = ROOT_DIR / "reports" / "training_corpus" / "corpus_split_report.md"


def _resolve_paths(root: Path) -> dict[str, Path]:
    return {
        "train": root / "datasets" / "training_corpus" / "train.jsonl",
        "validation": root / "datasets" / "training_corpus" / "validation.jsonl",
        "retrieval_only": root / "datasets" / "training_corpus" / "retrieval_only.jsonl",
        "review_required": root / "datasets" / "training_corpus" / "review_required.jsonl",
        "report_json": root / "reports" / "training_corpus" / "corpus_split_report.json",
        "report_md": root / "reports" / "training_corpus" / "corpus_split_report.md",
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        text = line.strip()
        if not text:
            continue
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def _deterministic_bucket(item_id: str) -> int:
    digest = hashlib.sha1(item_id.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 10


def _is_label_sparse(row: dict[str, Any]) -> bool:
    keep_label = str(row.get("keep_reject_label", "unlabeled")).strip().lower()
    if keep_label in {"", "unlabeled"}:
        return True
    if row.get("human_rating") in (None, ""):
        return True
    return False


def _is_train_validation_eligible(row: dict[str, Any]) -> tuple[bool, str]:
    if str(row.get("review_status", "")).lower() != "accepted":
        return False, "not_accepted"
    if row.get("training_allowed") is not True:
        return False, "training_not_allowed"
    if str(row.get("policy_status", "")).lower() != "complete":
        return False, "policy_incomplete"
    if _is_label_sparse(row):
        return False, "sparse_labels"
    if row.get("source_type") == "generated_midi_feedback" and str(row.get("review_status", "")).lower() != "accepted":
        return False, "generated_midi_requires_human_review"
    return True, "eligible"


def promote_reviewed_corpus_splits(input_path: Path = NORMALIZED_INPUT) -> dict[str, Any]:
    root = input_path.resolve().parent.parent.parent
    paths = _resolve_paths(root)
    rows = _read_jsonl(input_path)
    train_rows: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []
    retrieval_only_rows: list[dict[str, Any]] = []
    review_required_rows: list[dict[str, Any]] = []
    blocker_counts: Counter[str] = Counter()

    for row in rows:
        eligible, reason = _is_train_validation_eligible(row)
        if eligible:
            target = "validation" if _deterministic_bucket(str(row.get("item_id", ""))) in {0, 1} else "train"
            promoted = dict(row)
            promoted["split"] = target
            if target == "train":
                train_rows.append(promoted)
            else:
                validation_rows.append(promoted)
            continue

        blocker_counts[reason] += 1
        review_status = str(row.get("review_status", "review_required")).lower()
        if review_status == "review_required":
            queued = dict(row)
            queued["split"] = "review_required"
            review_required_rows.append(queued)
            continue
        retrieval_row = dict(row)
        retrieval_row["split"] = "retrieval_only"
        retrieval_only_rows.append(retrieval_row)

    _write_jsonl(paths["train"], train_rows)
    _write_jsonl(paths["validation"], validation_rows)
    _write_jsonl(paths["retrieval_only"], retrieval_only_rows)
    _write_jsonl(paths["review_required"], review_required_rows)

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "normalized_input_path": input_path.as_posix(),
        "total_input_rows": len(rows),
        "train_rows": len(train_rows),
        "validation_rows": len(validation_rows),
        "retrieval_only_rows": len(retrieval_only_rows),
        "review_required_rows": len(review_required_rows),
        "top_blockers": [{"reason": reason, "count": count} for reason, count in blocker_counts.most_common(10)],
        "rules": [
            "Only accepted + training_allowed=true + policy complete + non-sparse labels are promoted.",
            "Rows with missing policy fields cannot enter train/validation.",
            "Sparse labels are routed to retrieval/reviewer pools.",
            "Deterministic hash split (80/20) is used for train/validation assignment.",
            "Generated MIDI rows require human review before supervised use.",
        ],
    }
    paths["report_json"].parent.mkdir(parents=True, exist_ok=True)
    paths["report_json"].write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    lines = [
        "# Corpus Split Report",
        "",
        f"- total input rows: `{report['total_input_rows']}`",
        f"- train rows: `{report['train_rows']}`",
        f"- validation rows: `{report['validation_rows']}`",
        f"- retrieval-only rows: `{report['retrieval_only_rows']}`",
        f"- review-required rows: `{report['review_required_rows']}`",
        "",
        "## Top blockers",
    ]
    if report["top_blockers"]:
        for item in report["top_blockers"]:
            lines.append(f"- {item['reason']}: `{item['count']}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Rules"] + [f"- {item}" for item in report["rules"]])
    paths["report_md"].write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote reviewed corpus rows into deterministic dataset splits.")
    parser.add_argument("--input", default=str(NORMALIZED_INPUT), help="Path to normalized music corpus jsonl")
    args = parser.parse_args()
    input_path = Path(args.input)
    report = promote_reviewed_corpus_splits(input_path)
    root = input_path.resolve().parent.parent.parent
    paths = _resolve_paths(root)
    print(f"TRAIN_SPLIT_PATH={paths['train'].as_posix()}")
    print(f"VALIDATION_SPLIT_PATH={paths['validation'].as_posix()}")
    print(f"RETRIEVAL_ONLY_PATH={paths['retrieval_only'].as_posix()}")
    print(f"REVIEW_REQUIRED_PATH={paths['review_required'].as_posix()}")
    print(f"TRAIN_ROWS={report['train_rows']}")
    print(f"VALIDATION_ROWS={report['validation_rows']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

