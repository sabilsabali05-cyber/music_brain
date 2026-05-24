from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
INPUT_RECORDS = ROOT_DIR / "datasets" / "music_intelligence" / "music_intelligence_records.jsonl"

MAX_ITEMS = 50


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


def _priority(record: dict[str, Any]) -> tuple[float, float]:
    scores = record.get("scores", {})
    decision = record.get("promotion_decision", {})
    blockers = len(decision.get("blockers", []))
    retrieval = float(scores.get("retrieval_value_score", 0.0))
    training = float(scores.get("training_value_score", 0.0))
    near_eligible = max(0.0, training - 0.05 * blockers)
    return (retrieval + near_eligible) / 2.0, near_eligible


def _resolve_paths(root: Path) -> dict[str, Path]:
    return {
        "output_json": root / "reports" / "review_queue" / "music_intelligence_review_batch_001.json",
        "output_md": root / "reports" / "review_queue" / "music_intelligence_review_batch_001.md",
    }


def _review_questions() -> list[str]:
    return [
        "is this musically valuable?",
        "best time range",
        "junk/noisy time range",
        "harmony quality 1-10",
        "chord movement quality 1-10",
        "bass movement quality 1-10",
        "melodic contour quality 1-10",
        "motif usefulness 1-10",
        "rhythm/groove quality 1-10",
        "texture usefulness 1-10",
        "emotional value 1-10",
        "weirdness good/bad/neutral",
        "training policy: training_safe/retrieval_only/excluded/unsure",
        "reason",
        "tags",
        "notes",
    ]


def build_music_intelligence_review_form(input_records: Path = INPUT_RECORDS) -> dict[str, Any]:
    root = input_records.resolve().parent.parent.parent
    paths = _resolve_paths(root)
    rows = _read_jsonl(input_records)
    candidates = [row for row in rows if row.get("promotion_decision", {}).get("promotion_label") != "training_safe"]
    ranked = sorted(candidates, key=lambda row: _priority(row), reverse=True)
    selected = ranked[:MAX_ITEMS]

    items = []
    for row in selected:
        scores = row.get("scores", {})
        decision = row.get("promotion_decision", {})
        item = {
            "item_id": row.get("item_id"),
            "source_artifact": row.get("source_artifact"),
            "source_path_redacted": row.get("source_path_redacted"),
            "current_promotion_label": decision.get("promotion_label"),
            "current_blockers": decision.get("blockers", []),
            "retrieval_value_score": scores.get("retrieval_value_score"),
            "training_value_score": scores.get("training_value_score"),
            "questions": _review_questions(),
            "responses": {},
        }
        items.append(item)

    payload = {
        "batch_id": "music_intelligence_review_batch_001",
        "generated_at": datetime.now(UTC).isoformat(),
        "selection_size": len(items),
        "selection_strategy": "highest-value near-eligible records",
        "questions": _review_questions(),
        "items": items,
    }

    paths["output_json"].parent.mkdir(parents=True, exist_ok=True)
    paths["output_json"].write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    lines = [
        "# Music Intelligence Review Batch 001",
        "",
        f"- generated_at: `{payload['generated_at']}`",
        f"- selection_size: `{payload['selection_size']}`",
        f"- selection_strategy: `{payload['selection_strategy']}`",
        "",
        "## Questions",
    ]
    for question in payload["questions"]:
        lines.append(f"- {question}")
    lines.extend(["", "## Items"])
    for item in items:
        lines.append(
            f"- `{item['item_id']}` | retrieval_value=`{item['retrieval_value_score']}` | training_value=`{item['training_value_score']}`"
        )
    if not items:
        lines.append("- none")
    paths["output_md"].write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Build review form for music intelligence record validation.")
    parser.add_argument("--input", default=str(INPUT_RECORDS), help="Path to music intelligence records jsonl")
    args = parser.parse_args()
    input_path = Path(args.input)
    payload = build_music_intelligence_review_form(input_path)
    paths = _resolve_paths(input_path.resolve().parent.parent.parent)
    print(f"MUSIC_INTELLIGENCE_REVIEW_BATCH_JSON={paths['output_json'].as_posix()}")
    print(f"MUSIC_INTELLIGENCE_REVIEW_BATCH_MD={paths['output_md'].as_posix()}")
    print(f"MUSIC_INTELLIGENCE_REVIEW_BATCH_SIZE={payload['selection_size']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
