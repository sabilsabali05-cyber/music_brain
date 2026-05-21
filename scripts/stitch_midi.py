from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from mido import Message, MetaMessage, MidiFile, MidiTrack, second2tick


@dataclass
class WindowSummary:
    window_id: str
    index: int
    status: str
    core_start: float
    core_end: float
    global_start: float
    global_end: float
    midi_path: str | None


def _window_summaries(manifest: dict[str, object]) -> list[WindowSummary]:
    windows = manifest.get("transcription_windows", [])
    if not isinstance(windows, list):
        return []
    summaries: list[WindowSummary] = []
    for raw in windows:
        if not isinstance(raw, dict):
            continue
        summaries.append(
            WindowSummary(
                index=int(raw.get("index", 0) or 0),
                window_id=str(raw.get("window_id", f"win_{int(raw.get('index', 0) or 0):04d}")),
                status=str(raw.get("status", "unknown")),
                core_start=float(raw.get("core_start_seconds", 0.0) or 0.0),
                core_end=float(raw.get("core_end_seconds", 0.0) or 0.0),
                global_start=float(raw.get("global_start_seconds", 0.0) or 0.0),
                global_end=float(raw.get("global_end_seconds", 0.0) or 0.0),
                midi_path=str(raw.get("midi_path")) if raw.get("midi_path") else None,
            )
        )
    return summaries


def _abs_events_with_seconds(midi: MidiFile) -> list[tuple[float, Message | MetaMessage]]:
    events: list[tuple[float, Message | MetaMessage]] = []
    default_tempo = 500000
    for track in midi.tracks:
        absolute_seconds = 0.0
        current_tempo = default_tempo
        for message in track:
            delta_seconds = float(message.time) * current_tempo / 1_000_000.0 / max(1, midi.ticks_per_beat)
            absolute_seconds += delta_seconds
            events.append((absolute_seconds, message))
            if message.type == "set_tempo":
                current_tempo = int(getattr(message, "tempo", default_tempo))
    events.sort(key=lambda item: item[0])
    return events


def _build_merge_paths(manifest_path: Path, manifest: dict[str, object]) -> tuple[Path, Path]:
    run_dir = manifest.get("segmentation_run_dir")
    if isinstance(run_dir, str) and run_dir.strip():
        base_dir = Path(run_dir)
    else:
        base_dir = manifest_path.parent
    merged_dir = base_dir / "merged"
    merged_dir.mkdir(parents=True, exist_ok=True)
    return merged_dir / "merged_performance.mid", merged_dir / "merge_report.json"


def build_dry_run_lines(manifest_path: Path) -> list[str]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    windows = _window_summaries(manifest)

    lines: list[str] = []
    lines.append(f"manifest_path: {manifest_path.resolve().as_posix()}")
    lines.append(f"segmentation_run_id: {manifest.get('segmentation_run_id')}")
    lines.append(f"duration_seconds: {manifest.get('duration_seconds')}")
    lines.append("")

    windows_with_midi: list[WindowSummary] = []
    missing_or_failed: list[WindowSummary] = []
    for window in windows:
        status = window.status
        midi_path = str(window.midi_path or "")
        has_midi = bool(midi_path and Path(midi_path).exists())
        if status == "success" and has_midi:
            windows_with_midi.append(window)
        else:
            missing_or_failed.append(window)

    lines.append(f"windows_total: {len(windows)}")
    lines.append(f"windows_with_midi: {len(windows_with_midi)}")
    lines.append(f"windows_missing_or_failed: {len(missing_or_failed)}")
    lines.append("")
    lines.append("windows_with_midi:")
    if not windows_with_midi:
        lines.append("  - none")
    for window in windows_with_midi:
        core_start = window.core_start
        core_end = window.core_end
        global_start = window.global_start
        global_end = window.global_end
        lines.append(
            "  - "
            f"index={window.index} "
            f"status={window.status} "
            f"core=[{core_start:.3f},{core_end:.3f}] "
            f"global=[{global_start:.3f},{global_end:.3f}] "
            f"midi_path={window.midi_path} "
            f"estimated_global_placement=[{core_start:.3f},{core_end:.3f}]"
        )
        if (core_start > global_start) or (core_end < global_end):
            lines.append("    warning=context_overlap_present trim_to_core_required")
    lines.append("")
    lines.append("missing_or_failed_windows:")
    if not missing_or_failed:
        lines.append("  - none")
    for window in missing_or_failed:
        lines.append(
            "  - "
            f"index={window.index} "
            f"status={window.status} "
            f"core=[{window.core_start:.3f},{window.core_end:.3f}] "
            f"midi_path={window.midi_path}"
        )
    lines.append("")
    lines.append(
        "dry_run_notes: dry-run only; no files modified. Overlap/context warnings indicate where trimming and "
        "deduplication will be applied in a future non-dry-run implementation."
    )
    return lines


def stitch_manifest(manifest_path: Path, *, allow_partial: bool = False) -> tuple[Path, Path, dict[str, object]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    windows = _window_summaries(manifest)
    output_midi_path, report_path = _build_merge_paths(manifest_path, manifest)

    report: dict[str, object] = {
        "manifest_path": manifest_path.resolve().as_posix(),
        "output_midi_path": output_midi_path.resolve().as_posix(),
        "windows_total": len(windows),
        "windows_used": 0,
        "windows_skipped": 0,
        "skipped_window_ids": [],
        "partial_stitch": False,
        "warning": None,
        "events_read": 0,
        "events_kept": 0,
        "events_discarded_context": 0,
        "note_on_count": 0,
        "duration_seconds": float(manifest.get("duration_seconds", 0.0) or 0.0),
        "limitations": [
            "v1 uses one merged track and a fixed tempo map.",
            "Meta/program identity is only partially preserved.",
            "No advanced note-overlap de-dup beyond core-region trimming.",
        ],
        "status": "failed",
    }
    try:
        incomplete_windows = [window for window in windows if window.status != "success"]
        is_partial = len(incomplete_windows) > 0
        report["partial_stitch"] = is_partial
        if is_partial:
            report["warning"] = "partial stitch: merged MIDI does not represent full performance"
            if not allow_partial:
                skipped_ids = [window.window_id for window in incomplete_windows]
                report["windows_skipped"] = len(skipped_ids)
                report["skipped_window_ids"] = skipped_ids
                raise RuntimeError(
                    "Manifest has pending or failed windows. Re-run when complete or pass --allow-partial."
                )
        kept_events: list[tuple[float, Message | MetaMessage]] = []
        for window in windows:
            midi_path = Path(window.midi_path) if window.midi_path else None
            if window.status != "success" or midi_path is None or not midi_path.exists():
                report["windows_skipped"] = int(report["windows_skipped"]) + 1
                if isinstance(report["skipped_window_ids"], list):
                    report["skipped_window_ids"].append(window.window_id)
                continue
            report["windows_used"] = int(report["windows_used"]) + 1
            midi = MidiFile(str(midi_path))
            for local_seconds, message in _abs_events_with_seconds(midi):
                if message.type == "end_of_track":
                    continue
                report["events_read"] = int(report["events_read"]) + 1
                global_seconds = window.global_start + float(local_seconds)
                if global_seconds < window.core_start or global_seconds > window.core_end:
                    report["events_discarded_context"] = int(report["events_discarded_context"]) + 1
                    continue
                if message.is_meta and message.type not in {"set_tempo", "time_signature", "key_signature"}:
                    continue
                cloned = message.copy(time=0)
                kept_events.append((global_seconds, cloned))
                report["events_kept"] = int(report["events_kept"]) + 1
                if cloned.type == "note_on" and int(getattr(cloned, "velocity", 0)) > 0:
                    report["note_on_count"] = int(report["note_on_count"]) + 1

        kept_events.sort(key=lambda item: item[0])
        output_midi = MidiFile(ticks_per_beat=480)
        track = MidiTrack()
        output_midi.tracks.append(track)
        track.append(MetaMessage("set_tempo", tempo=500000, time=0))
        previous_seconds = 0.0
        for global_seconds, message in kept_events:
            delta_seconds = max(0.0, float(global_seconds) - previous_seconds)
            delta_ticks = int(round(second2tick(delta_seconds, output_midi.ticks_per_beat, 500000)))
            previous_seconds = float(global_seconds)
            track.append(message.copy(time=max(0, delta_ticks)))
        track.append(MetaMessage("end_of_track", time=0))
        output_midi.save(str(output_midi_path))
        report["status"] = "success"
    except Exception as exc:  # noqa: BLE001
        report["status"] = "failed"
        report.setdefault("limitations", [])
        if isinstance(report["limitations"], list):
            report["limitations"].append(f"stitch_error={exc.__class__.__name__}: {exc}")
        else:
            report["limitations"] = [f"stitch_error={exc.__class__.__name__}: {exc}"]
        raise
    finally:
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return output_midi_path.resolve(), report_path.resolve(), report


def main() -> int:
    parser = argparse.ArgumentParser(description="Stitch per-window MIDI for segmented transcriptions.")
    parser.add_argument("manifest_path", help="Path to segments_manifest.json")
    parser.add_argument("--dry-run", action="store_true", help="Print stitching plan without modifying files.")
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Allow stitching even when some manifest windows are pending/failed.",
    )
    args = parser.parse_args()
    manifest_path = Path(args.manifest_path)
    if args.dry_run:
        for line in build_dry_run_lines(manifest_path):
            print(line)
        return 0
    output_path, report_path, report = stitch_manifest(manifest_path, allow_partial=args.allow_partial)
    print(f"MERGED_MIDI_PATH={output_path.as_posix()}")
    print(f"MERGE_REPORT_PATH={report_path.as_posix()}")
    print(f"MERGE_STATUS={report.get('status')}")
    if report.get("status") != "success":
        raise SystemExit("MIDI stitching failed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
