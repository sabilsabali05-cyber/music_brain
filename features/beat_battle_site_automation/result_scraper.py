from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .site_config_schema import BeatBattleRankedSiteConfig


ALLOWED_RESULT_FIELDS = [
    "round_id",
    "user_handle",
    "placement",
    "score",
    "votes",
    "result_url",
    "result_available",
]


@dataclass(frozen=True)
class ResultIngestionResult:
    result_available: bool
    feedback_ingested: bool
    blocker: str | None
    result_record: dict[str, Any]


def _load_snapshot(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def ingest_result(config: BeatBattleRankedSiteConfig, project_root: Path) -> ResultIngestionResult:
    snapshot = _load_snapshot((project_root / config.session.manual_result_snapshot_path).resolve())
    if not snapshot:
        return ResultIngestionResult(
            result_available=False,
            feedback_ingested=False,
            blocker="missing_manual_result_snapshot",
            result_record={},
        )
    result_record = {key: snapshot.get(key) for key in ALLOWED_RESULT_FIELDS}
    result_record["user_handle"] = config.user_handle
    result_record["captured_at"] = datetime.now(UTC).isoformat()
    result_available = bool(result_record.get("result_available", False))
    if not result_available:
        return ResultIngestionResult(
            result_available=False,
            feedback_ingested=False,
            blocker="result_not_available",
            result_record=result_record,
        )

    results_path = (project_root / config.paths.round_results_jsonl).resolve()
    feedback_path = (project_root / config.paths.taste_feedback_jsonl).resolve()
    _append_jsonl(results_path, result_record)
    feedback_row = {
        "feedback_id": f"beat_battle_{result_record.get('round_id', 'unknown')}",
        "generation_id": f"beat_battle_round_{result_record.get('round_id', 'unknown')}",
        "candidate_id": "submitted_entry",
        "authorization_status": "self_owned",
        "source_authorized_for_learning": True,
        "reviewer": "self",
        "taste_label": "like" if int(result_record.get("placement", 9999) or 9999) <= 20 else "neutral",
        "accepted": True,
        "musicality_score": 0.6,
        "groove_score": 0.6,
        "harmony_score": 0.6,
        "result_available": True,
        "placement": result_record.get("placement"),
        "score": result_record.get("score"),
    }
    _append_jsonl(feedback_path, feedback_row)
    return ResultIngestionResult(
        result_available=True,
        feedback_ingested=True,
        blocker=None,
        result_record=result_record,
    )


def as_dict(result: ResultIngestionResult) -> dict[str, Any]:
    return {
        "result_available": result.result_available,
        "feedback_ingested": result.feedback_ingested,
        "blocker": result.blocker,
        "result_record": result.result_record,
    }
