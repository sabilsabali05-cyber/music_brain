from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.beat_battle_agent.sound_pair_archive import build_sound_pair_archive  # noqa: E402
from features.beat_battle_agent.sound_pair_listening_sheet import write_listening_sheet  # noqa: E402
from features.beat_battle_agent.sound_pair_record_schema import append_records_jsonl  # noqa: E402


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT_DIR.resolve()).as_posix()
    except Exception:  # noqa: BLE001
        return path.as_posix()


def _write_status_report(path: Path, payload: dict[str, Any], title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {title}", ""]
    for key, value in payload.items():
        if isinstance(value, list):
            value_text = ", ".join(str(item) for item in value) if value else "none"
        else:
            value_text = str(value)
        lines.append(f"- {key}: `{value_text}`")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def run_create_battle_sound_pair_record(project_root: Path, manual_manifest: str = "") -> dict[str, Any]:
    archive = build_sound_pair_archive(project_root, manual_manifest=manual_manifest)
    dataset_path = project_root / "datasets" / "beat_battle_agent" / "sound_pair_records.jsonl"
    reports_root = project_root / "reports" / "beat_battle_agent"
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    if not dataset_path.exists():
        dataset_path.write_text("", encoding="utf-8")

    payload: dict[str, Any] = {
        "sound_pair_record_created": False,
        "round_id": archive.round_id,
        "source_round_manifest_path": archive.round_manifest_path,
        "provided_sounds_logged_count": archive.provided_sounds_logged_count,
        "synplant_variations_generated_count": archive.synplant_variations_generated_count,
        "synplant_variations_pending_count": archive.synplant_variations_pending_count,
        "listening_sheet_path": archive.listening_sheet_md_path,
        "feedback_ready": False,
        "blockers": [archive.blocker] if archive.blocker else [],
    }

    def write_shared_status_files() -> None:
        shared_status = {
            "status": "ready" if payload["sound_pair_record_created"] else "blocked",
            "sound_pair_record_created": payload["sound_pair_record_created"],
            "provided_sounds_logged_count": payload["provided_sounds_logged_count"],
            "synplant_variations_generated_count": payload["synplant_variations_generated_count"],
            "synplant_variations_pending_count": payload["synplant_variations_pending_count"],
            "feedback_ready": payload["feedback_ready"],
            "blockers": payload["blockers"],
        }
        _write_status_report(reports_root / "study_agent_status.md", shared_status, "Beat Battle Study Agent Status")
        _write_status_report(reports_root / "synplant_catalog_status.md", shared_status, "Synplant Catalog Status")
        _write_status_report(reports_root / "battle_learning_status.md", shared_status, "Battle Learning Status")

    if archive.blocker:
        report_json = reports_root / "sound_pair_record_report.json"
        report_md = reports_root / "sound_pair_record_report.md"
        reports_root.mkdir(parents=True, exist_ok=True)
        report_json.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        _write_status_report(report_md, payload, "Sound Pair Record Report")
        write_shared_status_files()
        return payload

    append_records_jsonl(dataset_path, archive.records)
    write_listening_sheet(
        archive.records,
        html_path=project_root / archive.listening_sheet_html_path,
        md_path=project_root / archive.listening_sheet_md_path,
        review_notes_path=project_root / archive.review_notes_local_json_path,
    )

    payload["sound_pair_record_created"] = True
    payload["feedback_ready"] = True
    per_round_json = reports_root / f"{archive.round_id}_sound_pair_record.json"
    per_round_md = reports_root / f"{archive.round_id}_sound_pair_record.md"
    per_round_json.parent.mkdir(parents=True, exist_ok=True)
    per_round_json.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    _write_status_report(per_round_md, payload, "Beat Battle Sound Pair Record Report")

    write_shared_status_files()
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Create Beat Battle post-battle sound pair records.")
    parser.add_argument("--manifest", default="", help="Optional manual round manifest path relative to repo root.")
    args = parser.parse_args()
    payload = run_create_battle_sound_pair_record(ROOT_DIR, manual_manifest=args.manifest)
    print(f"SOUND_PAIR_RECORD_CREATED={str(payload['sound_pair_record_created']).lower()}")
    print(f"PROVIDED_SOUNDS_LOGGED_COUNT={payload['provided_sounds_logged_count']}")
    print(f"SYNPLANT_VARIATIONS_GENERATED_COUNT={payload['synplant_variations_generated_count']}")
    print(f"SYNPLANT_VARIATIONS_PENDING_COUNT={payload['synplant_variations_pending_count']}")
    print(f"LISTENING_SHEET_PATH={payload['listening_sheet_path']}")
    print(f"FEEDBACK_READY={str(payload['feedback_ready']).lower()}")
    if payload["blockers"]:
        print(f"BLOCKER={','.join(payload['blockers'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
