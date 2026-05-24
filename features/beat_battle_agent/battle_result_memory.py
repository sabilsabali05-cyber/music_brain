from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .winner_pattern_study import study_winner_patterns

LOCAL_RESULT_PATH = Path("reports/review_queue/beat_battle_result.local.json")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def ingest_local_battle_result(project_root: Path) -> dict[str, Any]:
    payload = _read_json(project_root / LOCAL_RESULT_PATH)
    if not payload:
        return {"ok": False, "blocker": "missing_local_result_file"}
    if payload.get("fake_result", False) is True:
        return {"ok": False, "blocker": "fake_results_not_allowed"}

    round_id = str(payload.get("round_id", "")).strip()
    draft_id = str(payload.get("draft_id", "")).strip()
    if not round_id or not draft_id:
        return {"ok": False, "blocker": "missing_round_or_draft_id"}

    result_row = {
        "result_id": f"{round_id}:{draft_id}",
        "round_id": round_id,
        "draft_id": draft_id,
        "placement": payload.get("placement"),
        "score": payload.get("score"),
        "submitted_manually": True,
        "manual_submission_confirmed": True,
        "result_logged_manually": True,
        "source": "user_logged_result",
        "training_allowed": True,
        "site_samples_used_for_training": False,
        "synplant_study_data_used_for_submission_training": False,
    }
    feedback_row = {
        "round_id": round_id,
        "draft_id": draft_id,
        "outcome": payload.get("outcome", "unknown"),
        "placement": payload.get("placement"),
        "score": payload.get("score"),
        "feedback_source": "beat_battle_manual_log",
        "allowed_metadata_only": True,
    }

    battle_results_path = project_root / "datasets" / "beat_battle_agent" / "battle_results.jsonl"
    feedback_path = project_root / "datasets" / "taste_learning" / "beat_battle_site_feedback.jsonl"
    _append_jsonl(battle_results_path, [result_row])
    _append_jsonl(feedback_path, [feedback_row])
    return {
        "ok": True,
        "blocker": "",
        "battle_results_path": battle_results_path.as_posix(),
        "feedback_path": feedback_path.as_posix(),
        "rows_written": 1,
    }


def analyze_battle_results(project_root: Path) -> dict[str, Any]:
    battle_results_path = project_root / "datasets" / "beat_battle_agent" / "battle_results.jsonl"
    rows = _read_jsonl(battle_results_path)
    winners = [row for row in rows if isinstance(row.get("placement"), int) and int(row["placement"]) <= 3]
    summary = {
        "results_count": len(rows),
        "winner_count": len(winners),
        "winner_rate": round((len(winners) / len(rows)), 4) if rows else 0.0,
        "blocker": "" if rows else "no_results_logged",
    }
    report_root = project_root / "reports" / "beat_battle_agent"
    report_root.mkdir(parents=True, exist_ok=True)
    (report_root / "battle_results_summary.md").write_text(
        "\n".join(
            [
                "# Battle Results Summary",
                "",
                f"- results_count: `{summary['results_count']}`",
                f"- winner_count: `{summary['winner_count']}`",
                f"- winner_rate: `{summary['winner_rate']}`",
                f"- blocker: `{summary['blocker'] or 'none'}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (report_root / "battle_results_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    study_winner_patterns(project_root, rows)
    return summary


def train_battle_outcome_ranker(project_root: Path) -> dict[str, Any]:
    battle_results_path = project_root / "datasets" / "beat_battle_agent" / "battle_results.jsonl"
    rows = _read_jsonl(battle_results_path)
    count = len(rows)
    status = {
        "results_count": count,
        "battle_outcome_ranker_status": "heuristic_baseline" if count < 20 else "local_train",
        "train_allowed_data_only": True,
        "used_site_raw_samples_for_training": False,
        "used_synplant_study_for_submission_training": False,
    }
    artifact_path = project_root / "artifacts" / "beat_battle_agent" / "battle_outcome_ranker_status.json"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(status, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return status
