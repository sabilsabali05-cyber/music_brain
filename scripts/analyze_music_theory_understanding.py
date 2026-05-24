from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.music_theory_understanding import build_theory_record


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


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _top(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    ranked = sorted(rows, key=lambda row: float(row.get(key, 0.0)), reverse=True)[:25]
    return [{"item_id": row["item_id"], key: row.get(key, 0.0)} for row in ranked]


def main() -> int:
    normalized_path = ROOT_DIR / "datasets" / "normalized_music_corpus" / "normalized_music_corpus.jsonl"
    retrieval_path = ROOT_DIR / "datasets" / "training_corpus" / "retrieval_only.jsonl"
    review_path = ROOT_DIR / "datasets" / "training_corpus" / "review_required.jsonl"
    intelligence_path = ROOT_DIR / "datasets" / "music_intelligence" / "music_intelligence_records.jsonl"

    out_jsonl = ROOT_DIR / "datasets" / "music_theory" / "theory_understanding_records.jsonl"
    report_json = ROOT_DIR / "reports" / "music_theory" / "music_theory_understanding_report.json"
    report_md = ROOT_DIR / "reports" / "music_theory" / "music_theory_understanding_report.md"

    normalized_rows = _read_jsonl(normalized_path)
    retrieval_rows = _read_jsonl(retrieval_path)
    review_rows = _read_jsonl(review_path)
    intelligence_rows = _read_jsonl(intelligence_path)
    intelligence_by_id = {str(row.get("item_id")): row for row in intelligence_rows}

    rows_considered = len(normalized_rows)
    rows_analyzed = 0
    rows_skipped = 0
    blocked_policy = 0
    blocked_confidence = 0
    records: list[dict[str, Any]] = []
    blocked_reasons = Counter()
    for row in normalized_rows:
        record = build_theory_record(row, intelligence_by_id.get(str(row.get("item_id"))))
        payload = record.to_dict()
        if record.blocked_by_policy:
            blocked_policy += 1
            blocked_reasons["policy"] += 1
        if record.blocked_by_confidence:
            blocked_confidence += 1
            blocked_reasons["confidence"] += 1
        if record.blocked_by_policy:
            rows_skipped += 1
            continue
        rows_analyzed += 1
        records.append(payload)

    _write_jsonl(out_jsonl, records)

    harmony_rows = [row for row in records if row["harmonic_interest_score"] >= 0.33]
    rhythm_rows = [row for row in records if row["rhythm_identity_score"] >= 0.33]
    motif_rows = [row for row in records if row["motif_reusability_score"] >= 0.33]
    voice_rows = [row for row in records if row["voice_leading_score"] >= 0.33]
    weird_rows = [row for row in records if row["harmony_understanding"]["valuable_weirdness"]]
    junk_rows = [row for row in records if row["random_note_penalty"] >= 0.6]
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "rows_considered": rows_considered,
        "rows_analyzed": rows_analyzed,
        "rows_skipped": rows_skipped,
        "rows_blocked_by_confidence": blocked_confidence,
        "rows_blocked_by_policy": blocked_policy,
        "rows_with_harmony_theory": len(harmony_rows),
        "rows_with_rhythm_theory": len(rhythm_rows),
        "rows_with_motif_theory": len(motif_rows),
        "rows_with_voice_leading_theory": len(voice_rows),
        "retrieval_only_rows_reference": len(retrieval_rows),
        "review_required_rows_reference": len(review_rows),
        "top_25_harmony_rich": _top(harmony_rows, "harmonic_interest_score"),
        "top_25_rhythm_rich": _top(rhythm_rows, "rhythm_identity_score"),
        "top_25_motif_rich": _top(motif_rows, "motif_reusability_score"),
        "top_25_voice_leading_rich": _top(voice_rows, "voice_leading_score"),
        "top_25_valuable_weirdness": _top(weird_rows, "harmonic_interest_score"),
        "top_25_random_keyboard_junk_moments": _top(junk_rows, "random_note_penalty"),
        "blocked_reasons": dict(blocked_reasons),
        "policy": {
            "no_cloud_calls": True,
            "no_model_training": True,
            "no_raw_media_processing": True,
            "no_fake_confidence_claims": True,
        },
    }
    _write_json(report_json, report)
    lines = [
        "# Music Theory Understanding Report",
        "",
        f"- rows considered: `{report['rows_considered']}`",
        f"- rows analyzed: `{report['rows_analyzed']}`",
        f"- rows skipped: `{report['rows_skipped']}`",
        f"- blocked by confidence: `{report['rows_blocked_by_confidence']}`",
        f"- blocked by policy: `{report['rows_blocked_by_policy']}`",
        f"- rows with harmony theory: `{report['rows_with_harmony_theory']}`",
        f"- rows with rhythm theory: `{report['rows_with_rhythm_theory']}`",
        f"- rows with motif theory: `{report['rows_with_motif_theory']}`",
        f"- rows with voice-leading theory: `{report['rows_with_voice_leading_theory']}`",
        "",
        "## Top 25 lists",
        "- harmony-rich: see report json",
        "- rhythm-rich: see report json",
        "- motif-rich: see report json",
        "- voice-leading-rich: see report json",
        "- valuable weirdness: see report json",
        "- random keyboard/junk moments: see report json",
    ]
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"THEORY_RECORDS_PATH={out_jsonl.as_posix()}")
    print(f"THEORY_REPORT_JSON={report_json.as_posix()}")
    print(f"THEORY_REPORT_MD={report_md.as_posix()}")
    print(f"ROWS_ANALYZED={rows_analyzed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
