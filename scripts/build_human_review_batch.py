from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
NORMALIZED_INPUT = ROOT_DIR / "datasets" / "normalized_music_corpus" / "normalized_music_corpus.jsonl"
SPLIT_REVIEW_REQUIRED = ROOT_DIR / "datasets" / "training_corpus" / "review_required.jsonl"
BATCH_JSON = ROOT_DIR / "reports" / "review_queue" / "human_review_batch_001.json"
BATCH_MD = ROOT_DIR / "reports" / "review_queue" / "human_review_batch_001.md"
MAX_BATCH_SIZE = 50


def _resolve_paths(root: Path) -> dict[str, Path]:
    return {
        "normalized_input": root / "datasets" / "normalized_music_corpus" / "normalized_music_corpus.jsonl",
        "review_required": root / "datasets" / "training_corpus" / "review_required.jsonl",
        "batch_json": root / "reports" / "review_queue" / "human_review_batch_001.json",
        "batch_md": root / "reports" / "review_queue" / "human_review_batch_001.md",
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


def _score_review_row(row: dict[str, Any]) -> float:
    score = 0.0
    tags = {str(tag).lower() for tag in row.get("tags", []) if isinstance(tag, str)}
    provenance = row.get("provenance")
    if "dense_region" in tags or "dense_activity" in tags:
        score += 3.0
    if "rhythm_dominant" in tags or "harmonic_density" in tags:
        score += 2.0
    if row.get("source_type") == "generated_midi_feedback":
        score += 3.0
    if row.get("training_allowed") is False and row.get("policy_status") == "complete":
        score += 1.5
    if row.get("review_reason"):
        score += 1.0
    if isinstance(provenance, dict) and provenance:
        score += 1.0
        confidence = provenance.get("confidence")
        if isinstance(confidence, (int, float)):
            score += float(confidence)
    if row.get("source_artifact", "").startswith("datasets/training_exports/"):
        score += 1.0
    return score


def _review_prompt(row: dict[str, Any], score: float) -> dict[str, Any]:
    return {
        "item_id": row.get("item_id"),
        "source_artifact": row.get("source_artifact"),
        "source_type": row.get("source_type"),
        "source_path_redacted": row.get("source_path_redacted"),
        "priority_score": round(score, 4),
        "current_status": {
            "authorization_status": row.get("authorization_status"),
            "review_status": row.get("review_status"),
            "training_allowed": row.get("training_allowed"),
            "policy_status": row.get("policy_status"),
            "excluded_reason": row.get("excluded_reason"),
        },
        "asks": {
            "keep_reject_retrieval_only": "keep/reject/retrieval_only",
            "training_allowed": "yes/no/unsure",
            "harmony_rating": "1-10",
            "melody_rating": "1-10",
            "rhythm_rating": "1-10",
            "texture_rating": "1-10",
            "emotional_value": "1-10",
            "weirdness": "good/bad/neutral",
            "notes": "free text",
            "tags": "comma-separated labels",
        },
    }


def build_human_review_batch(normalized_input: Path = NORMALIZED_INPUT) -> dict[str, Any]:
    root = normalized_input.resolve().parent.parent.parent
    paths = _resolve_paths(root)
    candidates = _read_jsonl(paths["review_required"])
    if not candidates:
        candidates = [
            row
            for row in _read_jsonl(normalized_input)
            if str(row.get("review_status", "")).lower() == "review_required"
        ]

    scored = sorted(((row, _score_review_row(row)) for row in candidates), key=lambda pair: pair[1], reverse=True)
    selected = scored[:MAX_BATCH_SIZE]
    batch_items = [_review_prompt(row, score) for row, score in selected]
    payload = {
        "batch_id": "human_review_batch_001",
        "generated_at": datetime.now(UTC).isoformat(),
        "selection_size": len(batch_items),
        "selection_rules": [
            "Prioritize musically dense/interesting rows.",
            "Prioritize rows with harmony/motif hints and stronger provenance.",
            "Prioritize near-eligible rows that can unblock train/validation.",
            "Include generated MIDI rows requiring preference labels.",
            "Cap batch at 50 items.",
        ],
        "items": batch_items,
    }
    paths["batch_json"].parent.mkdir(parents=True, exist_ok=True)
    paths["batch_json"].write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    lines = [
        "# Human Review Batch 001",
        "",
        f"- generated_at: `{payload['generated_at']}`",
        f"- selection_size: `{payload['selection_size']}`",
        "",
        "## Selection rules",
    ]
    lines.extend(f"- {rule}" for rule in payload["selection_rules"])
    lines.extend(["", "## Items"])
    for item in batch_items:
        lines.extend(
            [
                f"- item_id: `{item['item_id']}`",
                f"  - source_artifact: `{item['source_artifact']}`",
                f"  - source_type: `{item['source_type']}`",
                f"  - priority_score: `{item['priority_score']}`",
            ]
        )
    if not batch_items:
        lines.append("- none")
    paths["batch_md"].write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Build curated human-review batch for policy-gated corpus rows.")
    parser.add_argument("--input", default=str(NORMALIZED_INPUT), help="Path to normalized corpus jsonl")
    args = parser.parse_args()
    input_path = Path(args.input)
    payload = build_human_review_batch(input_path)
    root = input_path.resolve().parent.parent.parent
    paths = _resolve_paths(root)
    print(f"HUMAN_REVIEW_BATCH_PATH={paths['batch_json'].as_posix()}")
    print(f"HUMAN_REVIEW_BATCH_SIZE={payload['selection_size']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

