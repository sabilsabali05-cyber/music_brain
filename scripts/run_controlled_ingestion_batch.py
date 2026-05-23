from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.plan_controlled_ingestion_batch import plan_controlled_ingestion_batch

REPORT_DIR = ROOT_DIR / "reports" / "controlled_ingestion"
RUN_JSON = REPORT_DIR / "controlled_batch_run_report.json"
RUN_MD = REPORT_DIR / "controlled_batch_run_report.md"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Manifest must be a JSON object.")
    return payload


def run_controlled_ingestion_batch(manifest_path: Path, *, execute: bool = False) -> dict[str, Any]:
    planner_payload = plan_controlled_ingestion_batch(manifest_path=manifest_path)
    manifest = _read_json(manifest_path)
    errors = list(planner_payload.get("errors", []))
    warnings = list(planner_payload.get("warnings", []))

    if planner_payload.get("status") != "valid":
        status = "blocked_invalid_manifest"
    else:
        status = "dry_run_success"

    requested_actions = manifest.get("requested_actions", {})
    if not isinstance(requested_actions, dict):
        requested_actions = {}

    requested_transcription = bool(requested_actions.get("transcription_requested", False))
    requested_modal = bool(requested_actions.get("modal_requested", False))
    allow_transcription = bool(manifest.get("allow_transcription", False))
    allow_modal = bool(manifest.get("allow_modal", False))

    if requested_transcription and not allow_transcription:
        errors.append("Manifest requests transcription but allow_transcription is false.")
    if requested_modal and not allow_modal:
        errors.append("Manifest requests Modal but allow_modal is false.")

    song_files = manifest.get("song_files", [])
    if not isinstance(song_files, list):
        song_files = []

    skipped_unauthorized: list[dict[str, Any]] = []
    runnable_items: list[dict[str, Any]] = []
    for item in song_files:
        if not isinstance(item, dict):
            continue
        if not bool(item.get("authorized", False)):
            skipped_unauthorized.append(
                {
                    "path": str(item.get("path", "")),
                    "reason": "not_authorized",
                }
            )
            continue
        runnable_items.append(item)

    execution_notes: list[str] = []
    if execute and not errors:
        status = "execution_blocked_not_integrated"
        execution_notes.append("Execute mode requested.")
        execution_notes.append("Actual audio processing is intentionally not integrated in this sprint shell.")
        execution_notes.append("No transcription, no Modal calls, and no ingestion processing were performed.")
    elif not execute and not errors:
        status = "dry_run_success"
        execution_notes.append("Dry run only. No processing performed.")
    elif errors:
        status = "blocked_invalid_manifest"

    payload = {
        "status": status,
        "batch_id": str(manifest.get("batch_id", "unknown")),
        "manifest_path": manifest_path.as_posix(),
        "execute_requested": execute,
        "planner_status": planner_payload.get("status"),
        "runnable_item_count": len(runnable_items),
        "skipped_unauthorized_count": len(skipped_unauthorized),
        "skipped_unauthorized": skipped_unauthorized,
        "requested_actions": {
            "transcription_requested": requested_transcription,
            "modal_requested": requested_modal,
        },
        "permission_flags": {
            "allow_transcription": allow_transcription,
            "allow_modal": allow_modal,
        },
        "errors": errors,
        "warnings": warnings,
        "execution_notes": execution_notes,
        "provenance": {
            "runner": "scripts/run_controlled_ingestion_batch.py",
            "audio_processing_performed": False,
            "transcription_performed": False,
            "modal_calls_performed": False,
            "ingestion_integrated": False,
        },
        "limitations": [
            "Runner shell validates policy and readiness only in this phase.",
            "Execute mode intentionally refuses real ingestion until explicit integration.",
        ],
    }
    return payload


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Controlled Ingestion Batch Run Report",
        "",
        f"- status: `{payload['status']}`",
        f"- batch_id: `{payload['batch_id']}`",
        f"- execute_requested: `{payload['execute_requested']}`",
        f"- runnable_item_count: `{payload['runnable_item_count']}`",
        f"- skipped_unauthorized_count: `{payload['skipped_unauthorized_count']}`",
        "",
        "## Execution Notes",
    ]
    lines.extend([f"- {item}" for item in payload["execution_notes"]] or ["- none"])
    lines.extend(["", "## Errors"])
    lines.extend([f"- {item}" for item in payload["errors"]] or ["- none"])
    lines.extend(["", "## Warnings"])
    lines.extend([f"- {item}" for item in payload["warnings"]] or ["- none"])
    lines.extend(["", "## Limitations"])
    lines.extend([f"- {item}" for item in payload["limitations"]])
    lines.append("")
    return "\n".join(lines)


def write_run_report(manifest_path: Path, *, execute: bool) -> tuple[Path, Path, dict[str, Any]]:
    payload = run_controlled_ingestion_batch(manifest_path=manifest_path, execute=execute)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    RUN_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    RUN_MD.write_text(_render_markdown(payload), encoding="utf-8")
    batch_id = payload.get("batch_id", "unknown")
    run_dir = REPORT_DIR / "runs" / str(batch_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    run_state = {
        "batch_id": batch_id,
        "status": payload["status"],
        "execute_requested": payload["execute_requested"],
        "manifest_path": payload["manifest_path"],
        "runnable_item_count": payload["runnable_item_count"],
        "skipped_unauthorized_count": payload["skipped_unauthorized_count"],
        "errors": payload["errors"],
        "warnings": payload["warnings"],
    }
    (run_dir / "run_state.json").write_text(json.dumps(run_state, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    (run_dir / "controlled_batch_run_report.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    (run_dir / "controlled_batch_run_report.md").write_text(_render_markdown(payload), encoding="utf-8")
    return RUN_JSON, RUN_MD, payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Run controlled ingestion batch shell from a manifest.")
    parser.add_argument("manifest", help="Path to controlled batch manifest JSON")
    parser.add_argument("--execute", action="store_true", help="Request execute mode (still safe shell in this phase)")
    args = parser.parse_args()
    json_path, md_path, payload = write_run_report(Path(args.manifest), execute=args.execute)
    print(f"CONTROLLED_BATCH_RUN_JSON={json_path.as_posix()}")
    print(f"CONTROLLED_BATCH_RUN_MD={md_path.as_posix()}")
    print(f"CONTROLLED_BATCH_RUN_STATUS={payload['status']}")
    print(f"CONTROLLED_BATCH_RUN_ERRORS={len(payload['errors'])}")
    return 1 if payload["status"] == "blocked_invalid_manifest" else 0


if __name__ == "__main__":
    raise SystemExit(main())
