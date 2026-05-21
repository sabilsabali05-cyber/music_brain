from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_dry_run_lines(manifest_path: Path) -> list[str]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    windows = manifest.get("transcription_windows", [])
    if not isinstance(windows, list):
        windows = []

    lines: list[str] = []
    lines.append(f"manifest_path: {manifest_path.resolve().as_posix()}")
    lines.append(f"segmentation_run_id: {manifest.get('segmentation_run_id')}")
    lines.append(f"duration_seconds: {manifest.get('duration_seconds')}")
    lines.append("")

    windows_with_midi: list[dict[str, object]] = []
    missing_or_failed: list[dict[str, object]] = []
    for window in windows:
        if not isinstance(window, dict):
            continue
        status = str(window.get("status", "unknown"))
        midi_path = str(window.get("midi_path", "") or "")
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
        core_start = float(window.get("core_start_seconds", 0.0) or 0.0)
        core_end = float(window.get("core_end_seconds", 0.0) or 0.0)
        global_start = float(window.get("global_start_seconds", 0.0) or 0.0)
        global_end = float(window.get("global_end_seconds", 0.0) or 0.0)
        lines.append(
            "  - "
            f"index={window.get('index')} "
            f"status={window.get('status')} "
            f"core=[{core_start:.3f},{core_end:.3f}] "
            f"global=[{global_start:.3f},{global_end:.3f}] "
            f"midi_path={window.get('midi_path')} "
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
            f"index={window.get('index')} "
            f"status={window.get('status')} "
            f"core=[{float(window.get('core_start_seconds', 0.0) or 0.0):.3f},"
            f"{float(window.get('core_end_seconds', 0.0) or 0.0):.3f}] "
            f"midi_path={window.get('midi_path')}"
        )
    lines.append("")
    lines.append(
        "dry_run_notes: dry-run only; no files modified. Overlap/context warnings indicate where trimming and "
        "deduplication will be applied in a future non-dry-run implementation."
    )
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Stitch per-window MIDI for segmented transcriptions.")
    parser.add_argument("manifest_path", help="Path to segments_manifest.json")
    parser.add_argument("--dry-run", action="store_true", help="Print stitching plan without modifying files.")
    args = parser.parse_args()
    if not args.dry_run:
        raise SystemExit("Only --dry-run is currently implemented.")
    for line in build_dry_run_lines(Path(args.manifest_path)):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
