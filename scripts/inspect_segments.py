from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_inspection_lines(manifest: dict[str, object]) -> list[str]:
    lines: list[str] = []
    musical_segments = manifest.get("musical_segments", [])
    windows = manifest.get("transcription_windows", [])

    lines.append(f"performance_id: {manifest.get('performance_id')}")
    lines.append(f"source_name: {manifest.get('source_name')}")
    lines.append(f"duration_seconds: {manifest.get('duration_seconds')}")
    lines.append(f"segmentation_strategy: {manifest.get('segmentation_strategy')}")
    lines.append(f"strategy_requested: {manifest.get('strategy_requested')}")
    lines.append(f"strategy_used: {manifest.get('strategy_used')}")
    lines.append(f"fallback_used: {manifest.get('fallback_used')}")
    lines.append(f"segmentation_run_id: {manifest.get('segmentation_run_id')}")
    lines.append(f"musical_segments_count: {len(musical_segments) if isinstance(musical_segments, list) else 0}")
    lines.append(f"transcription_windows_count: {len(windows) if isinstance(windows, list) else 0}")

    lines.append("musical_segments:")
    if isinstance(musical_segments, list):
        for seg in musical_segments:
            if not isinstance(seg, dict):
                continue
            lines.append(
                "  - "
                f"index={seg.get('index')} "
                f"start={seg.get('global_start_seconds')} "
                f"end={seg.get('global_end_seconds')} "
                f"duration={seg.get('duration_seconds')} "
                f"prev={seg.get('previous_segment_id')} "
                f"next={seg.get('next_segment_id')} "
                f"boundary_confidence={seg.get('boundary_confidence')} "
                f"boundary_reason={seg.get('boundary_reason')} "
                f"transcription_window_id={seg.get('transcription_window_id')}"
            )

    lines.append("transcription_windows:")
    if isinstance(windows, list):
        for win in windows:
            if not isinstance(win, dict):
                continue
            line = (
                "  - "
                f"index={win.get('index')} "
                f"global_start={win.get('global_start_seconds')} "
                f"global_end={win.get('global_end_seconds')} "
                f"core_start={win.get('core_start_seconds')} "
                f"core_end={win.get('core_end_seconds')} "
                f"pre_context={win.get('pre_context_seconds')} "
                f"post_context={win.get('post_context_seconds')} "
                f"source_segment_ids={win.get('source_segment_ids')} "
                f"status={win.get('status')}"
            )
            if win.get("track_folder"):
                line += f" track_folder={win.get('track_folder')}"
            lines.append(line)
    return lines


def inspect_segments(manifest_path: Path) -> list[str]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return build_inspection_lines(manifest)


def main() -> int:
    parser = argparse.ArgumentParser(description="Print an inspection report for segments manifest.")
    parser.add_argument("manifest_path", help="Path to segments_manifest.json")
    args = parser.parse_args()

    for line in inspect_segments(Path(args.manifest_path)):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
