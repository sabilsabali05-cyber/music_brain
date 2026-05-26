from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

EXTRACTED_JSONL = ROOT_DIR / "datasets" / "source_loop_extraction" / "extracted_source_loops.jsonl"
WITNESS_JSONL = ROOT_DIR / "datasets" / "source_loop_extraction" / "source_loop_witness_observations.jsonl"
OUT_JSONL = ROOT_DIR / "datasets" / "source_loop_extraction" / "ranked_extracted_source_loops.jsonl"
REPORT_DIR = ROOT_DIR / "reports" / "source_loop_extraction"
REPORT_JSON = REPORT_DIR / "ranked_extracted_source_loops_report.json"
REPORT_MD = REPORT_DIR / "ranked_extracted_source_loops_report.md"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def _witness_counts(observations: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for row in observations:
        clip_id = str(row.get("item_id", "")).strip()
        if not clip_id:
            continue
        counters = out.setdefault(
            clip_id,
            {"real_backend": 0, "heuristic": 0, "unavailable": 0},
        )
        status = str(row.get("backend_status", "")).strip()
        if status == "real_backend" and bool(row.get("used_real_backend", False)):
            counters["real_backend"] += 1
        elif status == "unavailable":
            counters["unavailable"] += 1
        else:
            counters["heuristic"] += 1
    return out


def _score_loop(loop: dict[str, Any], counts: dict[str, int]) -> float:
    tempo_conf = float(loop.get("tempo_confidence", 0.0))
    loopability = float(loop.get("loopability_score", 0.0))
    rhythm = float(loop.get("rhythm_density_score", 0.0))
    duration = float(loop.get("duration_seconds", 0.0))
    duration_bonus = 0.0
    if 2.0 <= duration <= 20.0:
        duration_bonus = 0.08
    elif 1.5 <= duration <= 24.0:
        duration_bonus = 0.04
    real_bonus = min(0.15, counts.get("real_backend", 0) * 0.06)
    heuristic_bonus = min(0.12, counts.get("heuristic", 0) * 0.015)
    unavailable_penalty = min(0.09, counts.get("unavailable", 0) * 0.01)
    score = (
        loopability * 0.36
        + tempo_conf * 0.22
        + rhythm * 0.16
        + duration_bonus
        + real_bonus
        + heuristic_bonus
        - unavailable_penalty
    )
    return round(score, 6)


def main() -> int:
    extracted = _read_jsonl(EXTRACTED_JSONL)
    observations = _read_jsonl(WITNESS_JSONL)
    counts_by_clip = _witness_counts(observations)
    eligible = [
        row
        for row in extracted
        if bool(row.get("local_audio_clip_exists", False))
        and bool(row.get("authorized_for_buddy_generation", False))
    ]
    scored: list[dict[str, Any]] = []
    for row in eligible:
        clip_id = str(row.get("clip_id", "")).strip()
        counts = counts_by_clip.get(clip_id, {"real_backend": 0, "heuristic": 0, "unavailable": 0})
        enriched = dict(row)
        enriched["witness_counts"] = counts
        enriched["rank_score"] = _score_loop(row, counts)
        scored.append(enriched)
    scored.sort(key=lambda x: float(x.get("rank_score", 0.0)), reverse=True)

    selected_ids = {str(row.get("clip_id", "")) for row in scored[:12]}
    output_rows: list[dict[str, Any]] = []
    for idx, row in enumerate(scored, start=1):
        enriched = dict(row)
        enriched["rank_index"] = idx
        enriched["selected_for_midi_buddy_generation"] = str(row.get("clip_id", "")) in selected_ids
        output_rows.append(enriched)
    _write_jsonl(OUT_JSONL, output_rows)

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "eligible_clip_count": len(eligible),
        "ranked_clip_count": len(output_rows),
        "selected_actual_loops_count": len(selected_ids),
        "selected_clip_ids": sorted(selected_ids),
        "selection_rule": "top12_by_rank_score_from_local_audio_existing_authorized_loops",
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = [
        "# Ranked Extracted Source Loops Report",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- eligible_clip_count: `{report['eligible_clip_count']}`",
        f"- ranked_clip_count: `{report['ranked_clip_count']}`",
        f"- selected_actual_loops_count: `{report['selected_actual_loops_count']}`",
        f"- selection_rule: `{report['selection_rule']}`",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"RANKED_EXTRACTED_SOURCE_LOOPS_JSONL={OUT_JSONL.as_posix()}")
    print(f"RANKED_EXTRACTED_SOURCE_LOOPS_REPORT_MD={REPORT_MD.as_posix()}")
    print(f"RANKED_EXTRACTED_SOURCE_LOOPS_REPORT_JSON={REPORT_JSON.as_posix()}")
    print(f"SELECTED_ACTUAL_LOOPS_COUNT={len(selected_ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
