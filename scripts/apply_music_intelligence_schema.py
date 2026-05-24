from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.music_intelligence.music_intelligence_schema import MusicIntelligenceRecord
from features.music_intelligence.music_intelligence_scoring import compute_music_intelligence_scores
from features.music_intelligence.promotion_rules import decide_promotion_label


NORMALIZED_INPUT = ROOT_DIR / "datasets" / "normalized_music_corpus" / "normalized_music_corpus.jsonl"
REVIEW_REQUIRED_INPUT = ROOT_DIR / "datasets" / "training_corpus" / "review_required.jsonl"
RETRIEVAL_ONLY_INPUT = ROOT_DIR / "datasets" / "training_corpus" / "retrieval_only.jsonl"


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


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if isinstance(parsed, dict):
        return parsed
    return {}


def _resolve_paths(root: Path) -> dict[str, Path]:
    return {
        "output_jsonl": root / "datasets" / "music_intelligence" / "music_intelligence_records.jsonl",
        "output_report_json": root / "reports" / "music_intelligence" / "music_intelligence_schema_application_report.json",
        "output_report_md": root / "reports" / "music_intelligence" / "music_intelligence_schema_application_report.md",
        "normalized_report_input": root / "reports" / "database" / "normalized_music_corpus_report.json",
        "split_report_input": root / "reports" / "training_corpus" / "corpus_split_report.json",
    }


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def _is_complete_policy(row: dict[str, Any]) -> bool:
    return str(row.get("policy_status", "")).lower() == "complete"


def _has_labels(row: dict[str, Any]) -> bool:
    keep_reject = str(row.get("keep_reject_label", "unlabeled")).lower()
    return keep_reject != "unlabeled"


def _row_with_scores_and_decision(row: dict[str, Any]) -> tuple[dict[str, Any], list[str], str]:
    record = MusicIntelligenceRecord.from_normalized_row(row)
    scores = compute_music_intelligence_scores(record)
    decision = decide_promotion_label(record, scores)
    payload = record.to_dict()
    payload["scores"] = scores
    payload["promotion_decision"] = decision.__dict__
    return payload, decision.blockers, decision.promotion_label


def _closest_training_safe_score(record: dict[str, Any]) -> tuple[float, float]:
    scores = record.get("scores", {})
    decision = record.get("promotion_decision", {})
    training_value = float(scores.get("training_value_score", 0.0))
    blocker_count = float(len(decision.get("blockers", [])))
    closeness = max(0.0, training_value - 0.05 * blocker_count)
    return closeness, training_value


def apply_music_intelligence_schema(
    normalized_input: Path = NORMALIZED_INPUT,
    review_required_input: Path = REVIEW_REQUIRED_INPUT,
    retrieval_only_input: Path = RETRIEVAL_ONLY_INPUT,
) -> dict[str, Any]:
    root = normalized_input.resolve().parent.parent.parent
    paths = _resolve_paths(root)
    normalized_rows = _read_jsonl(normalized_input)
    review_required_rows = _read_jsonl(review_required_input)
    retrieval_only_rows = _read_jsonl(retrieval_only_input)
    normalized_report = _read_json(paths["normalized_report_input"])
    split_report = _read_json(paths["split_report_input"])

    processed_records: list[dict[str, Any]] = []
    blockers = Counter()
    counts = Counter()
    complete_tempo = 0
    complete_harmony = 0
    complete_rhythm = 0
    complete_texture = 0
    with_value_moments = 0
    with_junk_moments = 0
    missing_policy_count = 0
    missing_label_count = 0

    for row in normalized_rows:
        processed, row_blockers, label = _row_with_scores_and_decision(row)
        processed_records.append(processed)
        blockers.update(row_blockers)
        counts[label] += 1

        tempo = processed["tempo_structure"]
        harmony = processed["harmony_tonality"]
        rhythm = processed["rhythm"]
        texture = processed["texture_instrumentation"]
        if bool(tempo.get("has_complete_tempo_structure")):
            complete_tempo += 1
        if bool(harmony.get("has_complete_harmony_fields")):
            complete_harmony += 1
        if bool(rhythm.get("has_complete_rhythm_fields")):
            complete_rhythm += 1
        if bool(texture.get("has_complete_texture_fields")):
            complete_texture += 1
        if processed.get("valuable_moments"):
            with_value_moments += 1
        if processed.get("junk_moments"):
            with_junk_moments += 1

        if not _is_complete_policy(row):
            missing_policy_count += 1
        if not _has_labels(row):
            missing_label_count += 1

    by_retrieval_value = sorted(
        processed_records,
        key=lambda item: float(item.get("scores", {}).get("retrieval_value_score", 0.0)),
        reverse=True,
    )
    top_retrieval = [
        {
            "item_id": row.get("item_id"),
            "retrieval_value_score": row.get("scores", {}).get("retrieval_value_score", 0.0),
            "promotion_label": row.get("promotion_decision", {}).get("promotion_label"),
        }
        for row in by_retrieval_value[:25]
    ]

    by_training_closeness = sorted(
        [row for row in processed_records if row.get("promotion_decision", {}).get("promotion_label") != "training_safe"],
        key=lambda item: _closest_training_safe_score(item),
        reverse=True,
    )
    top_closest = [
        {
            "item_id": row.get("item_id"),
            "training_value_score": row.get("scores", {}).get("training_value_score", 0.0),
            "blockers": row.get("promotion_decision", {}).get("blockers", []),
            "promotion_label": row.get("promotion_decision", {}).get("promotion_label"),
        }
        for row in by_training_closeness[:25]
    ]

    paths["output_jsonl"].parent.mkdir(parents=True, exist_ok=True)
    with paths["output_jsonl"].open("w", encoding="utf-8") as handle:
        for row in processed_records:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "total_rows_processed": len(processed_records),
        "records_with_complete_tempo_structure_fields": complete_tempo,
        "records_with_complete_harmony_fields": complete_harmony,
        "records_with_complete_rhythm_fields": complete_rhythm,
        "records_with_complete_texture_fields": complete_texture,
        "records_with_valuable_moments": with_value_moments,
        "records_with_junk_moments": with_junk_moments,
        "training_safe_count": counts.get("training_safe", 0),
        "retrieval_only_count": counts.get("retrieval_only", 0),
        "excluded_count": counts.get("excluded", 0),
        "missing_policy_count": missing_policy_count,
        "missing_label_count": missing_label_count,
        "top_blockers": [{"blocker": key, "count": value} for key, value in blockers.most_common(10)],
        "top_25_highest_retrieval_value_records": top_retrieval,
        "top_25_closest_to_training_safe_records": top_closest,
        "input_sources": {
            "normalized_music_corpus": _relative_path(normalized_input, root),
            "review_required": _relative_path(review_required_input, root),
            "retrieval_only": _relative_path(retrieval_only_input, root),
            "normalized_report": _relative_path(paths["normalized_report_input"], root),
            "corpus_split_report": _relative_path(paths["split_report_input"], root),
        },
        "context": {
            "review_required_rows": len(review_required_rows),
            "retrieval_only_rows": len(retrieval_only_rows),
            "normalized_report_total_rows": normalized_report.get("total_rows"),
            "split_report_total_rows": split_report.get("total_input_rows"),
        },
    }

    paths["output_report_json"].parent.mkdir(parents=True, exist_ok=True)
    paths["output_report_json"].write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    lines = [
        "# Music Intelligence Schema Application Report",
        "",
        f"- total rows processed: `{report['total_rows_processed']}`",
        f"- records with complete tempo/structure fields: `{report['records_with_complete_tempo_structure_fields']}`",
        f"- records with complete harmony fields: `{report['records_with_complete_harmony_fields']}`",
        f"- records with complete rhythm fields: `{report['records_with_complete_rhythm_fields']}`",
        f"- records with complete texture fields: `{report['records_with_complete_texture_fields']}`",
        f"- records with valuable moments: `{report['records_with_valuable_moments']}`",
        f"- records with junk moments: `{report['records_with_junk_moments']}`",
        f"- training_safe count: `{report['training_safe_count']}`",
        f"- retrieval_only count: `{report['retrieval_only_count']}`",
        f"- excluded count: `{report['excluded_count']}`",
        f"- missing policy count: `{report['missing_policy_count']}`",
        f"- missing label count: `{report['missing_label_count']}`",
        "",
        "## Top blockers",
    ]
    if report["top_blockers"]:
        for item in report["top_blockers"]:
            lines.append(f"- {item['blocker']}: `{item['count']}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Top 25 highest retrieval value records"])
    for item in report["top_25_highest_retrieval_value_records"]:
        lines.append(
            f"- `{item['item_id']}` | retrieval_value_score=`{item['retrieval_value_score']}` | label=`{item['promotion_label']}`"
        )
    if not report["top_25_highest_retrieval_value_records"]:
        lines.append("- none")

    lines.extend(["", "## Top 25 closest-to-training-safe records"])
    for item in report["top_25_closest_to_training_safe_records"]:
        lines.append(
            f"- `{item['item_id']}` | training_value_score=`{item['training_value_score']}` | blockers=`{', '.join(item['blockers'])}`"
        )
    if not report["top_25_closest_to_training_safe_records"]:
        lines.append("- none")

    paths["output_report_md"].write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply strict music intelligence schema and promotion rubric.")
    parser.add_argument("--input", default=str(NORMALIZED_INPUT), help="Path to normalized corpus jsonl")
    args = parser.parse_args()
    input_path = Path(args.input)
    report = apply_music_intelligence_schema(input_path)
    paths = _resolve_paths(input_path.resolve().parent.parent.parent)
    print(f"MUSIC_INTELLIGENCE_RECORDS_PATH={paths['output_jsonl'].as_posix()}")
    print(f"MUSIC_INTELLIGENCE_REPORT_JSON={paths['output_report_json'].as_posix()}")
    print(f"MUSIC_INTELLIGENCE_REPORT_MD={paths['output_report_md'].as_posix()}")
    print(f"MUSIC_INTELLIGENCE_TOTAL_ROWS={report['total_rows_processed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
