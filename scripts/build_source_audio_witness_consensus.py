from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.model_witnesses import ModelWitnessConsensus

OBS_PATH = ROOT_DIR / "datasets" / "model_witnesses" / "source_audio_witness_observations.jsonl"
OUT_DIR = ROOT_DIR / "datasets" / "model_witnesses"
OUT_JSONL = OUT_DIR / "source_audio_witness_consensus.jsonl"
REPORT_DIR = ROOT_DIR / "reports" / "model_witnesses"
REPORT_JSON = REPORT_DIR / "source_audio_witness_consensus_report.json"
REPORT_MD = REPORT_DIR / "source_audio_witness_consensus_report.md"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


def _group_by_item(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        item_id = str(row.get("item_id", "")).strip()
        if not item_id:
            continue
        out.setdefault(item_id, []).append(row)
    return out


def _consensus_for_item(item_id: str, rows: list[dict[str, Any]]) -> ModelWitnessConsensus:
    agreeing = [str(row.get("witness_id", "")) for row in rows if row.get("backend_status") != "unavailable"]
    disagreements = [
        {
            "witness_id": str(row.get("witness_id", "")),
            "reason": "backend_unavailable" if row.get("backend_status") == "unavailable" else "heuristic_only",
            "evidence_summary": str(row.get("evidence_summary", "")),
        }
        for row in rows
        if row.get("backend_status") == "unavailable" or row.get("heuristic_witness_label")
    ]
    qualitative_conflicts = [f"{row['witness_id']}: {row['reason']}" for row in disagreements]
    weak_evidence = []
    if not agreeing:
        weak_evidence.append("no_real_backend_confirmation")
    if disagreements:
        weak_evidence.append("witnesses_disagree_or_missing")
    principles = [
        "Favor transformation over copying source phrases.",
        "Use meter and section hints as direction, not rigid templates.",
    ]
    rejected = [
        "Do not claim direct source-audio intent reconstruction.",
        "Do not average away contradictory witness observations.",
    ]
    confidence = 0.2 if not agreeing else 0.45
    return ModelWitnessConsensus(
        consensus_id=f"{item_id}__consensus",
        item_id=item_id,
        consensus_summary="Consensus preserves disagreements and marks weak evidence explicitly.",
        confidence=confidence,
        witness_count=len(rows),
        agreeing_witnesses=agreeing,
        disagreements=disagreements,
        qualitative_conflicts=qualitative_conflicts,
        weak_evidence_areas=weak_evidence,
        generative_principles=principles,
        rejected_principles=rejected,
        blockers=["insufficient_real_backends"] if not agreeing else [],
    )


def build_consensus() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = _read_jsonl(OBS_PATH)
    grouped = _group_by_item(rows)
    consensus_rows = [_consensus_for_item(item_id, item_rows).to_dict() for item_id, item_rows in sorted(grouped.items())]
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "items_considered": len(grouped),
        "consensus_records_created": len(consensus_rows),
        "items_with_disagreement": sum(1 for row in consensus_rows if row.get("disagreements")),
        "items_with_weak_evidence": sum(1 for row in consensus_rows if row.get("weak_evidence_areas")),
        "blockers": sorted({tag for row in consensus_rows for tag in row.get("blockers", [])}),
        "policy_notes": [
            "No blind averaging: disagreements are carried into consensus rows.",
            "Unavailable witnesses stay unavailable and are not fabricated.",
        ],
    }
    return consensus_rows, report


def write_outputs(consensus_rows: list[dict[str, Any]], report: dict[str, Any]) -> tuple[Path, Path, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_JSONL.open("w", encoding="utf-8") as handle:
        for row in consensus_rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")
    REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = [
        "# Source Audio Witness Consensus Report",
        "",
        f"- items_considered: `{report['items_considered']}`",
        f"- consensus_records_created: `{report['consensus_records_created']}`",
        f"- items_with_disagreement: `{report['items_with_disagreement']}`",
        f"- items_with_weak_evidence: `{report['items_with_weak_evidence']}`",
        "",
        "## Policy notes",
        *[f"- {row}" for row in report["policy_notes"]],
    ]
    REPORT_MD.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return OUT_JSONL, REPORT_JSON, REPORT_MD


def main() -> int:
    rows, report = build_consensus()
    out_path, json_path, md_path = write_outputs(rows, report)
    print(f"SOURCE_AUDIO_WITNESS_CONSENSUS={out_path.as_posix()}")
    print(f"SOURCE_AUDIO_WITNESS_CONSENSUS_REPORT_JSON={json_path.as_posix()}")
    print(f"SOURCE_AUDIO_WITNESS_CONSENSUS_REPORT_MD={md_path.as_posix()}")
    print(f"CONSENSUS_RECORDS_CREATED={report['consensus_records_created']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
