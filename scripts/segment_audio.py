from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def safe_source_name(path: Path) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", path.stem).strip("_") or "performance"


def probe_duration_seconds(source_path: Path) -> float:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(source_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {(result.stderr or '').strip()}")
    try:
        return float((result.stdout or "").strip())
    except ValueError as exc:
        raise RuntimeError("Could not parse duration from ffprobe output") from exc


def build_fixed_windows(
    *,
    duration_seconds: float,
    target_window_seconds: float,
    max_window_seconds: float,
    context_seconds: float,
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    if target_window_seconds <= 0:
        raise ValueError("target_window_seconds must be > 0")
    if max_window_seconds < target_window_seconds:
        raise ValueError("max_window_seconds must be >= target_window_seconds")

    musical_segments: list[dict[str, object]] = []
    transcription_windows: list[dict[str, object]] = []
    adjacency: list[dict[str, object]] = []

    core_start = 0.0
    index = 0
    while core_start < duration_seconds:
        core_end = min(duration_seconds, core_start + target_window_seconds)
        segment_id = f"seg_{index:04d}"
        window_id = f"win_{index:04d}"
        previous_segment_id = f"seg_{index - 1:04d}" if index > 0 else None
        next_segment_id = f"seg_{index + 1:04d}" if core_end < duration_seconds else None

        window_start = max(0.0, core_start - context_seconds)
        window_end = min(duration_seconds, core_end + context_seconds)

        musical_segments.append(
            {
                "segment_id": segment_id,
                "index": index,
                "global_start_seconds": round(core_start, 6),
                "global_end_seconds": round(core_end, 6),
                "duration_seconds": round(core_end - core_start, 6),
                "boundary_confidence": 0.2,
                "boundary_reason": "fixed_window_fallback",
                "previous_segment_id": previous_segment_id,
                "next_segment_id": next_segment_id,
                "section_label": None,
                "phrase_label": None,
                "local_summary": "Fixed fallback segment. Hybrid phrase detection scaffold pending.",
                "pre_context_seconds": round(min(context_seconds, core_start), 6),
                "post_context_seconds": round(min(context_seconds, duration_seconds - core_end), 6),
                "transcription_window_id": window_id,
            }
        )

        transcription_windows.append(
            {
                "window_id": window_id,
                "index": index,
                "global_start_seconds": round(window_start, 6),
                "global_end_seconds": round(window_end, 6),
                "core_start_seconds": round(core_start, 6),
                "core_end_seconds": round(core_end, 6),
                "pre_context_seconds": round(core_start - window_start, 6),
                "post_context_seconds": round(window_end - core_end, 6),
                "source_segment_ids": [segment_id],
                "chunk_audio_path": None,
                "status": "pending",
                "track_folder": None,
                "job_report": None,
                "midi_path": None,
                "error": None,
            }
        )

        if previous_segment_id is not None:
            adjacency.append(
                {
                    "from_segment_id": previous_segment_id,
                    "to_segment_id": segment_id,
                    "relation": "next",
                    "weight": 1.0,
                }
            )

        core_start = core_end
        index += 1

    return musical_segments, transcription_windows, adjacency


def extract_window_audio(source_path: Path, output_path: Path, start: float, end: float) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    duration = max(0.0, end - start)
    command = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{start}",
        "-t",
        f"{duration}",
        "-i",
        str(source_path),
        "-vn",
        str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed extracting window: {(result.stderr or '').strip()}")


def segment_audio(
    source_path: Path,
    *,
    strategy: str,
    target_window_seconds: float,
    max_window_seconds: float,
    context_seconds: float,
) -> Path:
    if not source_path.exists():
        raise FileNotFoundError(f"Audio file does not exist: {source_path}")

    duration_seconds = probe_duration_seconds(source_path)
    source_name_safe = safe_source_name(source_path)
    segment_root = Path("samples") / "segments" / source_name_safe
    windows_root = segment_root / "windows"
    segment_root.mkdir(parents=True, exist_ok=True)

    musical_segments, transcription_windows, adjacency = build_fixed_windows(
        duration_seconds=duration_seconds,
        target_window_seconds=target_window_seconds,
        max_window_seconds=max_window_seconds,
        context_seconds=context_seconds,
    )

    manifest_strategy = "fixed_with_context" if strategy == "fixed" else "hybrid_scaffold"
    if strategy == "hybrid":
        for segment in musical_segments:
            segment["boundary_reason"] = "hybrid_scaffold_fixed_baseline"
            segment["local_summary"] = (
                "Hybrid scaffold active; phrase-aware detectors are TODO. "
                "Fixed core windows with context currently used."
            )

    for window in transcription_windows:
        window_index = int(window["index"])
        chunk_path = windows_root / f"window_{window_index:04d}.wav"
        extract_window_audio(
            source_path=source_path,
            output_path=chunk_path,
            start=float(window["global_start_seconds"]),
            end=float(window["global_end_seconds"]),
        )
        window["chunk_audio_path"] = chunk_path.resolve().as_posix()

    manifest = {
        "performance_id": f"perf_{source_name_safe}",
        "source_path": source_path.resolve().as_posix(),
        "source_name": source_path.name,
        "duration_seconds": round(duration_seconds, 6),
        "segmentation_strategy": manifest_strategy,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "musical_segments": musical_segments,
        "transcription_windows": transcription_windows,
        "context_graph": {"adjacency": adjacency},
    }

    manifest_path = segment_root / "segments_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Create segmentation manifest and context-padded windows.")
    parser.add_argument("source_path", help="Path to input performance audio.")
    parser.add_argument("--strategy", choices=["fixed", "hybrid"], default="hybrid")
    parser.add_argument("--target-window-seconds", type=float, default=60.0)
    parser.add_argument("--max-window-seconds", type=float, default=90.0)
    parser.add_argument("--context-seconds", type=float, default=5.0)
    args = parser.parse_args()

    manifest_path = segment_audio(
        Path(args.source_path),
        strategy=args.strategy,
        target_window_seconds=args.target_window_seconds,
        max_window_seconds=args.max_window_seconds,
        context_seconds=args.context_seconds,
    )
    print(manifest_path.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
