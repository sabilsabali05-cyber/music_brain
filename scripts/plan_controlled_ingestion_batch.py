from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT_DIR / "reports" / "controlled_ingestion"
PLAN_JSON = REPORT_DIR / "controlled_batch_plan.json"
PLAN_MD = REPORT_DIR / "controlled_batch_plan.md"

DEFAULT_MAX_SONG_FILES = 5
DEFAULT_MAX_SAMPLE_LIBRARY_ITEMS = 100


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Manifest must be a JSON object.")
    return payload


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:  # noqa: BLE001
        return default


def _normalize_source(value: Any) -> str:
    return str(value or "").strip().lower()


def _validate_song_item(item: Any, index: int, errors: list[str], warnings: list[str]) -> tuple[bool, bool]:
    if not isinstance(item, dict):
        errors.append(f"song_files[{index}] must be an object.")
        return False, False
    path = str(item.get("path", "")).strip()
    if not path:
        errors.append(f"song_files[{index}] missing path.")
    lowered = path.lower().replace("\\", "/")
    if lowered.endswith("/") or "*" in lowered:
        errors.append(f"song_files[{index}] appears to be folder/wildcard mass dump: {path}")
    authorized = bool(item.get("authorized", False))
    if not authorized:
        errors.append(f"song_files[{index}] is not explicitly authorized.")
    source = _normalize_source(item.get("source"))
    training_allowed = bool(item.get("training_allowed", False))
    if "splice" in source and training_allowed:
        errors.append(f"song_files[{index}] uses Splice source with training_allowed=true.")
    if "splice" in source and not training_allowed:
        warnings.append(f"song_files[{index}] references Splice source and is not training-authorized.")
    return authorized, training_allowed


def plan_controlled_ingestion_batch(manifest_path: Path) -> dict[str, Any]:
    manifest = _read_json(manifest_path)
    errors: list[str] = []
    warnings: list[str] = []

    authorization_required = bool(manifest.get("authorization_required", True))
    if not authorization_required:
        errors.append("authorization_required must be true.")

    max_song_files = _safe_int(manifest.get("max_song_files"), DEFAULT_MAX_SONG_FILES)
    max_sample_library_items = _safe_int(
        manifest.get("max_sample_library_items"),
        DEFAULT_MAX_SAMPLE_LIBRARY_ITEMS,
    )
    if max_song_files > DEFAULT_MAX_SONG_FILES:
        errors.append(f"max_song_files cannot exceed {DEFAULT_MAX_SONG_FILES}.")
    if max_sample_library_items > DEFAULT_MAX_SAMPLE_LIBRARY_ITEMS:
        errors.append(f"max_sample_library_items cannot exceed {DEFAULT_MAX_SAMPLE_LIBRARY_ITEMS}.")

    allow_modal = bool(manifest.get("allow_modal", False))
    allow_transcription = bool(manifest.get("allow_transcription", False))
    allow_training_export = bool(manifest.get("allow_training_export", False))

    song_files = manifest.get("song_files", [])
    if not isinstance(song_files, list):
        errors.append("song_files must be a list.")
        song_files = []
    sample_filters = manifest.get("sample_library_filters", [])
    if not isinstance(sample_filters, list):
        errors.append("sample_library_filters must be a list.")
        sample_filters = []

    if len(song_files) > max_song_files:
        errors.append(f"song_files count {len(song_files)} exceeds max_song_files={max_song_files}.")

    requested_sample_items = 0
    for idx, item in enumerate(sample_filters):
        if not isinstance(item, dict):
            errors.append(f"sample_library_filters[{idx}] must be an object.")
            continue
        requested_sample_items += _safe_int(item.get("max_items_requested"), 0)
        source = _normalize_source(item.get("source"))
        training_allowed = bool(item.get("training_allowed", False))
        if "splice" in source and training_allowed:
            errors.append(f"sample_library_filters[{idx}] uses Splice source with training_allowed=true.")
    if requested_sample_items > max_sample_library_items:
        errors.append(
            "Requested sample-library items exceed max_sample_library_items: "
            f"{requested_sample_items} > {max_sample_library_items}."
        )

    authorized_song_count = 0
    training_eligible_song_count = 0
    for idx, item in enumerate(song_files):
        authorized, training_allowed = _validate_song_item(item, idx, errors, warnings)
        if authorized:
            authorized_song_count += 1
        if training_allowed:
            training_eligible_song_count += 1

    if allow_training_export and training_eligible_song_count == 0:
        errors.append("allow_training_export=true requires at least one training-eligible authorized item.")

    estimated_artifacts = {
        "performance_manifests": authorized_song_count,
        "post_ingestion_tangible_regeneration": 1 if authorized_song_count > 0 else 0,
        "post_ingestion_ableton_export": 1 if authorized_song_count > 0 else 0,
    }
    estimated_review_burden = {
        "manual_song_reviews": authorized_song_count,
        "manual_sample_reviews": min(max_sample_library_items, requested_sample_items),
        "estimated_total_review_actions": authorized_song_count + min(max_sample_library_items, requested_sample_items),
        "burden_level": (
            "low"
            if authorized_song_count <= 2 and requested_sample_items <= 30
            else "medium"
            if authorized_song_count <= 5 and requested_sample_items <= 100
            else "high"
        ),
    }

    status = "invalid" if errors else "valid"
    payload = {
        "status": status,
        "manifest_path": manifest_path.as_posix(),
        "batch_id": manifest.get("batch_id", "unknown"),
        "batch_goal": manifest.get("batch_goal", ""),
        "authorization_required": authorization_required,
        "allow_modal": allow_modal,
        "allow_transcription": allow_transcription,
        "allow_training_export": allow_training_export,
        "max_song_files": max_song_files,
        "max_sample_library_items": max_sample_library_items,
        "song_files_count": len(song_files),
        "authorized_song_files_count": authorized_song_count,
        "requested_sample_items": requested_sample_items,
        "estimated_artifacts": estimated_artifacts,
        "estimated_review_burden": estimated_review_burden,
        "errors": errors,
        "warnings": warnings,
        "provenance": {
            "planner": "scripts/plan_controlled_ingestion_batch.py",
            "audio_processing_performed": False,
            "transcription_performed": False,
            "modal_calls_performed": False,
        },
        "limitations": [
            "Planner validates manifest policy only; it does not process or inspect audio.",
            "Review-burden estimate is heuristic and should be confirmed manually.",
        ],
    }
    return payload


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Controlled Ingestion Batch Plan",
        "",
        f"- status: `{payload['status']}`",
        f"- batch_id: `{payload['batch_id']}`",
        f"- authorization_required: `{payload['authorization_required']}`",
        f"- song_files_count: `{payload['song_files_count']}`",
        f"- authorized_song_files_count: `{payload['authorized_song_files_count']}`",
        f"- requested_sample_items: `{payload['requested_sample_items']}`",
        "",
        "## Estimated Artifacts",
    ]
    for key, value in payload["estimated_artifacts"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Estimated Review Burden"])
    for key, value in payload["estimated_review_burden"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Errors"])
    lines.extend([f"- {item}" for item in payload["errors"]] or ["- none"])
    lines.extend(["", "## Warnings"])
    lines.extend([f"- {item}" for item in payload["warnings"]] or ["- none"])
    lines.extend(["", "## Limitations"])
    lines.extend([f"- {item}" for item in payload["limitations"]])
    lines.append("")
    return "\n".join(lines)


def write_plan_report(manifest_path: Path) -> tuple[Path, Path, dict[str, Any]]:
    payload = plan_controlled_ingestion_batch(manifest_path=manifest_path)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    PLAN_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    PLAN_MD.write_text(_render_markdown(payload), encoding="utf-8")
    return PLAN_JSON, PLAN_MD, payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan a controlled ingestion batch from an explicit manifest.")
    parser.add_argument("manifest", help="Path to controlled batch manifest JSON")
    args = parser.parse_args()
    json_path, md_path, payload = write_plan_report(Path(args.manifest))
    print(f"CONTROLLED_BATCH_PLAN_JSON={json_path.as_posix()}")
    print(f"CONTROLLED_BATCH_PLAN_MD={md_path.as_posix()}")
    print(f"CONTROLLED_BATCH_PLAN_STATUS={payload['status']}")
    print(f"CONTROLLED_BATCH_PLAN_ERRORS={len(payload['errors'])}")
    return 1 if payload["status"] != "valid" else 0


if __name__ == "__main__":
    raise SystemExit(main())
