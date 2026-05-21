from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SOURCE_REASONS = {"initial", "resume", "force_analysis", "force_segmentation", "manual_attach"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm_path(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _run_id_from_segments_path(segments_manifest_path: str | None) -> str:
    if not segments_manifest_path:
        return "unknown_run"
    path = Path(segments_manifest_path)
    return path.parent.name or "unknown_run"


def load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Expected object JSON at: {path}")
    return payload


def save_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def window_counts_for_segments_manifest(segments_manifest_path: str | None) -> tuple[int, int, int]:
    if not segments_manifest_path:
        return 0, 0, 0
    path = Path(segments_manifest_path)
    if not path.exists():
        return 0, 0, 0
    payload = load_json(path)
    windows = payload.get("transcription_windows", [])
    if not isinstance(windows, list):
        return 0, 0, 0
    successful = 0
    failed = 0
    for window in windows:
        if not isinstance(window, dict):
            continue
        status = str(window.get("status", "pending"))
        if status == "success":
            successful += 1
        elif status == "failed":
            failed += 1
    remaining = max(0, len(windows) - successful - failed)
    return successful, failed, remaining


def infer_analysis_path_from_segments_manifest(segments_manifest_path: str | None) -> str | None:
    if not segments_manifest_path:
        return None
    path = Path(segments_manifest_path)
    if not path.exists():
        return None
    payload = load_json(path)
    diagnostics = payload.get("segmentation_diagnostics", {})
    if isinstance(diagnostics, dict):
        diagnostics_path = _norm_path(diagnostics.get("analysis_path"))
        if diagnostics_path:
            return Path(diagnostics_path).resolve().as_posix()
    musical_segments = payload.get("musical_segments", [])
    if isinstance(musical_segments, list):
        for segment in musical_segments:
            if not isinstance(segment, dict):
                continue
            value = _norm_path(segment.get("analysis_path"))
            if value:
                return Path(value).resolve().as_posix()
    return None


def infer_merged_midi_from_segments_manifest(segments_manifest_path: str | None) -> str | None:
    if not segments_manifest_path:
        return None
    segments_path = Path(segments_manifest_path)
    merged_path = segments_path.parent / "merged" / "merged_performance.mid"
    if merged_path.exists():
        return merged_path.resolve().as_posix()
    return None


def _build_run_entry(
    *,
    run_id: str,
    analysis_path: str | None,
    segments_manifest_path: str | None,
    merged_midi_path: str | None,
    status: str,
    source_reason: str,
    created_at: str | None = None,
) -> dict[str, object]:
    if source_reason not in SOURCE_REASONS:
        source_reason = "manual_attach"
    successful, failed, remaining = window_counts_for_segments_manifest(segments_manifest_path)
    return {
        "run_id": run_id,
        "analysis_path": analysis_path,
        "segments_manifest_path": segments_manifest_path,
        "merged_midi_path": merged_midi_path,
        "status": status,
        "created_at": created_at or _now_iso(),
        "source_reason": source_reason,
        "successful_windows": successful,
        "failed_windows": failed,
        "remaining_windows": remaining,
    }


def _ensure_run_history_list(manifest: dict[str, object]) -> list[dict[str, object]]:
    run_history = manifest.get("run_history")
    if isinstance(run_history, list):
        typed: list[dict[str, object]] = []
        for item in run_history:
            if isinstance(item, dict):
                typed.append(item)
        manifest["run_history"] = typed
        return typed
    manifest["run_history"] = []
    return manifest["run_history"]  # type: ignore[return-value]


def _upsert_run_history(manifest: dict[str, object], entry: dict[str, object]) -> None:
    run_history = _ensure_run_history_list(manifest)
    run_id = str(entry.get("run_id", "unknown_run"))
    for index, existing in enumerate(run_history):
        if str(existing.get("run_id", "")) == run_id:
            existing_created = _norm_path(existing.get("created_at"))
            merged = dict(existing)
            merged.update(entry)
            if existing_created:
                merged["created_at"] = existing_created
            run_history[index] = merged
            return
    run_history.append(entry)


def _run_exists(manifest: dict[str, object], run_id: str) -> bool:
    run_history = _ensure_run_history_list(manifest)
    return any(str(item.get("run_id", "")) == run_id for item in run_history)


def ensure_run_tracking_fields(manifest: dict[str, object]) -> None:
    active_analysis_path = _norm_path(manifest.get("active_analysis_path")) or _norm_path(manifest.get("analysis_path"))
    active_segments_manifest_path = _norm_path(manifest.get("active_segments_manifest_path")) or _norm_path(
        manifest.get("segments_manifest_path")
    )
    active_merged_midi_path = _norm_path(manifest.get("active_merged_midi_path")) or _norm_path(
        manifest.get("merged_midi_path")
    )

    if not active_analysis_path:
        active_analysis_path = infer_analysis_path_from_segments_manifest(active_segments_manifest_path)
    if not active_merged_midi_path:
        active_merged_midi_path = infer_merged_midi_from_segments_manifest(active_segments_manifest_path)

    manifest["active_analysis_path"] = active_analysis_path
    manifest["active_segments_manifest_path"] = active_segments_manifest_path
    manifest["active_merged_midi_path"] = active_merged_midi_path
    # Keep legacy fields in sync for backward compatibility.
    manifest["analysis_path"] = active_analysis_path
    manifest["segments_manifest_path"] = active_segments_manifest_path
    manifest["merged_midi_path"] = active_merged_midi_path

    _ensure_run_history_list(manifest)
    if active_segments_manifest_path:
        run_id = _run_id_from_segments_path(active_segments_manifest_path)
        if not _run_exists(manifest, run_id):
            entry = _build_run_entry(
                run_id=run_id,
                analysis_path=active_analysis_path,
                segments_manifest_path=active_segments_manifest_path,
                merged_midi_path=active_merged_midi_path,
                status="active",
                source_reason="initial",
            )
            _upsert_run_history(manifest, entry)


def archive_active_run(manifest: dict[str, object], *, source_reason: str) -> None:
    ensure_run_tracking_fields(manifest)
    active_segments_manifest_path = _norm_path(manifest.get("active_segments_manifest_path"))
    if not active_segments_manifest_path:
        return
    entry = _build_run_entry(
        run_id=_run_id_from_segments_path(active_segments_manifest_path),
        analysis_path=_norm_path(manifest.get("active_analysis_path")),
        segments_manifest_path=active_segments_manifest_path,
        merged_midi_path=_norm_path(manifest.get("active_merged_midi_path")),
        status="archived",
        source_reason=source_reason,
    )
    _upsert_run_history(manifest, entry)


def set_active_run(
    manifest: dict[str, object],
    *,
    segments_manifest_path: str,
    source_reason: str,
    preserve_previous_as_history: bool = True,
) -> None:
    if source_reason not in SOURCE_REASONS:
        raise ValueError(f"Unsupported source_reason: {source_reason}")
    normalized_segments = Path(segments_manifest_path).resolve().as_posix()
    if not Path(normalized_segments).exists():
        raise FileNotFoundError(f"Segments manifest missing: {normalized_segments}")

    _ensure_run_history_list(manifest)
    previous_segments = _norm_path(manifest.get("active_segments_manifest_path"))
    if preserve_previous_as_history and previous_segments and previous_segments != normalized_segments:
        archive_active_run(manifest, source_reason=source_reason)

    if previous_segments == normalized_segments:
        analysis_path = _norm_path(manifest.get("active_analysis_path")) or infer_analysis_path_from_segments_manifest(
            normalized_segments
        )
    else:
        analysis_path = infer_analysis_path_from_segments_manifest(normalized_segments) or _norm_path(
            manifest.get("active_analysis_path")
        )
    merged_midi_path = infer_merged_midi_from_segments_manifest(normalized_segments)
    if not merged_midi_path and previous_segments == normalized_segments:
        merged_midi_path = _norm_path(manifest.get("active_merged_midi_path"))

    manifest["active_analysis_path"] = analysis_path
    manifest["active_segments_manifest_path"] = normalized_segments
    manifest["active_merged_midi_path"] = merged_midi_path
    manifest["analysis_path"] = analysis_path
    manifest["segments_manifest_path"] = normalized_segments
    manifest["merged_midi_path"] = merged_midi_path

    run_entry = _build_run_entry(
        run_id=_run_id_from_segments_path(normalized_segments),
        analysis_path=analysis_path,
        segments_manifest_path=normalized_segments,
        merged_midi_path=merged_midi_path,
        status="active",
        source_reason=source_reason,
    )
    _upsert_run_history(manifest, run_entry)


def summarize_runs(manifest: dict[str, object]) -> dict[str, Any]:
    ensure_run_tracking_fields(manifest)
    history = manifest.get("run_history", [])
    runs: list[dict[str, Any]] = []
    if isinstance(history, list):
        for item in history:
            if not isinstance(item, dict):
                continue
            run_id = str(item.get("run_id", "unknown_run"))
            analysis_path = _norm_path(item.get("analysis_path"))
            segments_manifest_path = _norm_path(item.get("segments_manifest_path"))
            merged_midi_path = _norm_path(item.get("merged_midi_path"))
            status = str(item.get("status", "unknown"))
            source_reason = str(item.get("source_reason", "unknown"))
            successful = int(item.get("successful_windows", 0) or 0)
            failed = int(item.get("failed_windows", 0) or 0)
            remaining = int(item.get("remaining_windows", 0) or 0)
            runs.append(
                {
                    "run_id": run_id,
                    "analysis_path": analysis_path,
                    "segments_manifest_path": segments_manifest_path,
                    "merged_midi_path": merged_midi_path,
                    "status": status,
                    "source_reason": source_reason,
                    "successful_windows": successful,
                    "failed_windows": failed,
                    "remaining_windows": remaining,
                }
            )

    return {
        "performance_id": _norm_path(manifest.get("performance_id")),
        "active_analysis_path": _norm_path(manifest.get("active_analysis_path")),
        "active_segments_manifest_path": _norm_path(manifest.get("active_segments_manifest_path")),
        "active_merged_midi_path": _norm_path(manifest.get("active_merged_midi_path")),
        "runs": runs,
    }
