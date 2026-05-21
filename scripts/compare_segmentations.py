from __future__ import annotations

import argparse
import json
from pathlib import Path

from mido import MidiFile


def _note_on_count(midi_path: Path) -> int:
    midi = MidiFile(str(midi_path))
    return sum(
        1
        for track in midi.tracks
        for message in track
        if getattr(message, "type", "") == "note_on" and getattr(message, "velocity", 0) > 0
    )


def summarize_manifest(manifest_path: Path) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    windows = manifest.get("transcription_windows", [])
    diagnostics = manifest.get("segmentation_diagnostics", {}) if isinstance(manifest, dict) else {}
    successful = 0
    failed = 0
    note_on_total = 0
    for window in windows if isinstance(windows, list) else []:
        if not isinstance(window, dict):
            continue
        status = window.get("status")
        if status == "success":
            successful += 1
            midi_path = window.get("midi_path")
            if midi_path and Path(str(midi_path)).exists():
                note_on_total += _note_on_count(Path(str(midi_path)))
        elif status == "failed":
            failed += 1

    return {
        "run_id": manifest.get("segmentation_run_id", manifest_path.parent.name),
        "strategy_requested": manifest.get("strategy_requested"),
        "strategy_used": manifest.get("strategy_used", manifest.get("segmentation_strategy")),
        "fallback_used": manifest.get("fallback_used", diagnostics.get("fallback_used")),
        "musical_segments": len(manifest.get("musical_segments", [])),
        "transcription_windows": len(windows) if isinstance(windows, list) else 0,
        "detected_boundary_count": diagnostics.get("detected_boundary_count"),
        "accepted_boundary_count": diagnostics.get("accepted_boundary_count"),
        "successful_windows": successful,
        "failed_windows": failed,
        "total_note_on_count": note_on_total,
        "manifest_path": manifest_path.resolve().as_posix(),
    }


def compare_segmentations(source_folder: Path) -> list[dict[str, object]]:
    manifests: list[Path] = []
    if (source_folder / "segments_manifest.json").exists():
        manifests.append(source_folder / "segments_manifest.json")
    else:
        for child in sorted(source_folder.iterdir()):
            if not child.is_dir():
                continue
            manifest_path = child / "segments_manifest.json"
            if manifest_path.exists():
                manifests.append(manifest_path)
    summaries = [summarize_manifest(path) for path in manifests]
    return summaries


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare segmentation runs for one source folder.")
    parser.add_argument("source_folder", help="Path to samples/segments/<safe_source_name>/")
    args = parser.parse_args()

    source_folder = Path(args.source_folder)
    summaries = compare_segmentations(source_folder)
    if not summaries:
        print("No segmentation manifests found.")
        return 0

    header = [
        "run_id",
        "strategy_requested",
        "strategy_used",
        "fallback_used",
        "musical_segments",
        "transcription_windows",
        "detected_boundary_count",
        "accepted_boundary_count",
        "successful_windows",
        "failed_windows",
        "total_note_on_count",
        "manifest_path",
    ]
    print("\t".join(header))
    for row in summaries:
        print("\t".join(str(row.get(col, "")) for col in header))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
