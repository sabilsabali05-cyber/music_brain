from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT_DIR.resolve()).as_posix()
    except Exception:  # noqa: BLE001
        return path.as_posix()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _latest_review_notes_path(project_root: Path) -> Path | None:
    candidates = sorted(
        (project_root / "local_battle_records").glob("*/review_notes.local.json"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def _write_markdown(path: Path, title: str, payload: dict[str, Any]) -> None:
    lines = [f"# {title}", ""]
    for key, value in payload.items():
        if isinstance(value, list):
            rendered = ", ".join(str(item) for item in value) if value else "none"
        else:
            rendered = str(value)
        lines.append(f"- {key}: `{rendered}`")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def run_feedback_ingestion(project_root: Path) -> dict[str, Any]:
    review_path = _latest_review_notes_path(project_root)
    reports_root = project_root / "reports" / "beat_battle_agent"
    synplant_feedback_path = project_root / "datasets" / "beat_battle_agent" / "synplant_variation_feedback.jsonl"
    sound_design_feedback_path = project_root / "datasets" / "taste_learning" / "sound_design_feedback.jsonl"
    report_md = reports_root / "sound_pair_feedback_ingestion_report.md"
    synplant_feedback_path.parent.mkdir(parents=True, exist_ok=True)
    sound_design_feedback_path.parent.mkdir(parents=True, exist_ok=True)
    if not synplant_feedback_path.exists():
        synplant_feedback_path.write_text("", encoding="utf-8")
    if not sound_design_feedback_path.exists():
        sound_design_feedback_path.write_text("", encoding="utf-8")

    def write_status_updates(payload: dict[str, Any]) -> None:
        status_payload = {
            "status": "ready" if payload["feedback_ready"] else "blocked",
            "feedback_ready": payload["feedback_ready"],
            "accepted_feedback_count": payload["accepted_feedback_count"],
            "blockers": payload["blockers"],
        }
        _write_markdown(reports_root / "battle_learning_status.md", "Battle Learning Status", status_payload)
        _write_markdown(reports_root / "study_agent_status.md", "Beat Battle Study Agent Status", status_payload)
        _write_markdown(reports_root / "synplant_catalog_status.md", "Synplant Catalog Status", status_payload)

    if review_path is None:
        payload = {
            "feedback_ready": False,
            "accepted_feedback_count": 0,
            "blockers": ["missing_review_notes_local_json"],
            "review_notes_path": "",
            "synplant_variation_feedback_dataset": _repo_rel(synplant_feedback_path),
            "sound_design_feedback_dataset": _repo_rel(sound_design_feedback_path),
        }
        _write_markdown(report_md, "Sound Pair Feedback Ingestion Report", payload)
        write_status_updates(payload)
        return payload

    review_payload = _read_json(review_path)
    reviews = review_payload.get("reviews", [])
    if not isinstance(reviews, list):
        reviews = []

    accepted_synplant_rows: list[dict[str, Any]] = []
    accepted_sound_design_rows: list[dict[str, Any]] = []
    for row in reviews:
        if not isinstance(row, dict):
            continue
        pair_id = str(row.get("sound_pair_id", "")).strip()
        winner = str(row.get("winner", "skip")).strip().lower()
        if not pair_id:
            continue
        base = {
            "sound_pair_id": pair_id,
            "winner": winner,
            "preserve_character_score": int(row.get("preserve_character_score", 0)),
            "uniqueness_score": int(row.get("uniqueness_score", 0)),
            "mix_ready": bool(row.get("mix_ready", False)),
            "notes": str(row.get("notes", "")).strip(),
        }
        accepted_synplant_rows.append(dict(base))
        accepted_sound_design_rows.append(dict(base))

    _append_jsonl(synplant_feedback_path, accepted_synplant_rows)
    _append_jsonl(sound_design_feedback_path, accepted_sound_design_rows)

    payload = {
        "feedback_ready": True,
        "accepted_feedback_count": len(accepted_synplant_rows),
        "blockers": [],
        "review_notes_path": _repo_rel(review_path),
        "synplant_variation_feedback_dataset": _repo_rel(synplant_feedback_path),
        "sound_design_feedback_dataset": _repo_rel(sound_design_feedback_path),
    }
    _write_markdown(report_md, "Sound Pair Feedback Ingestion Report", payload)
    write_status_updates(payload)
    return payload


def main() -> int:
    payload = run_feedback_ingestion(ROOT_DIR)
    print(f"FEEDBACK_READY={str(payload['feedback_ready']).lower()}")
    print(f"ACCEPTED_FEEDBACK_COUNT={payload['accepted_feedback_count']}")
    if payload["blockers"]:
        print(f"BLOCKER={','.join(payload['blockers'])}")
    print(f"SYNPLANT_FEEDBACK_DATASET={payload['synplant_variation_feedback_dataset']}")
    print(f"SOUND_DESIGN_FEEDBACK_DATASET={payload['sound_design_feedback_dataset']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
