from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median

from mido import MidiFile, tick2second


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Expected JSON object at: {path}")
    return payload


def save_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


@dataclass
class MidiSource:
    kind: str
    path: Path
    window_id: str | None
    start_seconds: float | None
    end_seconds: float | None


def get_active_paths(performance_manifest: dict[str, object]) -> tuple[Path, Path | None, Path | None]:
    segments_value = str(
        performance_manifest.get("active_segments_manifest_path")
        or performance_manifest.get("segments_manifest_path")
        or ""
    ).strip()
    if not segments_value:
        raise RuntimeError("Performance manifest missing active_segments_manifest_path.")
    segments_manifest_path = Path(segments_value)

    analysis_value = str(
        performance_manifest.get("active_analysis_path")
        or performance_manifest.get("analysis_path")
        or ""
    ).strip()
    merged_value = str(
        performance_manifest.get("active_merged_midi_path")
        or performance_manifest.get("merged_midi_path")
        or ""
    ).strip()

    analysis_path = Path(analysis_value) if analysis_value else None
    merged_midi_path = Path(merged_value) if merged_value else None
    return segments_manifest_path, analysis_path, merged_midi_path


def performance_metadata(performance_manifest: dict[str, object], segments_manifest_path: Path) -> tuple[str, str, str]:
    performance_id = str(performance_manifest.get("performance_id") or "unknown_performance")
    source_name = str(performance_manifest.get("source_name") or "unknown_source")
    segment_run_id = segments_manifest_path.parent.name or "unknown_segment_run"
    return performance_id, source_name, segment_run_id


def default_feature_dir(performance_id: str, segment_run_id: str) -> Path:
    return Path("features") / "performances" / performance_id / segment_run_id


def summarize_window_counts(segments_manifest: dict[str, object]) -> dict[str, int]:
    windows = segments_manifest.get("transcription_windows", [])
    if not isinstance(windows, list):
        return {"total": 0, "successful": 0, "failed": 0, "remaining": 0}
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
    return {
        "total": len(windows),
        "successful": successful,
        "failed": failed,
        "remaining": max(0, len(windows) - successful - failed),
    }


def collect_midi_sources(
    *,
    segments_manifest: dict[str, object],
    merged_midi_path: Path | None,
) -> tuple[list[MidiSource], list[str], str]:
    limitations: list[str] = []
    if merged_midi_path and merged_midi_path.exists():
        return (
            [MidiSource(kind="merged", path=merged_midi_path.resolve(), window_id=None, start_seconds=None, end_seconds=None)],
            limitations,
            "merged",
        )

    windows = segments_manifest.get("transcription_windows", [])
    sources: list[MidiSource] = []
    if isinstance(windows, list):
        for window in windows:
            if not isinstance(window, dict):
                continue
            if str(window.get("status", "pending")) != "success":
                continue
            midi_value = str(window.get("midi_path") or "").strip()
            if not midi_value:
                continue
            midi_path = Path(midi_value)
            if not midi_path.exists():
                continue
            sources.append(
                MidiSource(
                    kind="window",
                    path=midi_path.resolve(),
                    window_id=str(window.get("window_id") or ""),
                    start_seconds=float(window.get("core_start_seconds", 0.0) or 0.0),
                    end_seconds=float(window.get("core_end_seconds", 0.0) or 0.0),
                )
            )

    if sources:
        limitations.append("merged MIDI missing; falling back to successful window MIDIs.")
        return sources, limitations, "window_fallback"

    limitations.append("no merged MIDI and no successful window MIDI sources available.")
    return [], limitations, "no_midi"


def midi_note_events(midi_path: Path) -> list[tuple[float, int, int]]:
    midi = MidiFile(str(midi_path))
    events: list[tuple[float, int, int]] = []
    for track in midi.tracks:
        tempo = 500000
        absolute_seconds = 0.0
        for message in track:
            absolute_seconds += tick2second(message.time, midi.ticks_per_beat, tempo)
            if message.type == "set_tempo":
                tempo = int(getattr(message, "tempo", tempo))
            if message.type == "note_on" and int(getattr(message, "velocity", 0)) > 0:
                events.append((absolute_seconds, int(message.note), int(message.velocity)))
    events.sort(key=lambda item: item[0])
    return events


def rhythm_features_from_events(events: list[tuple[float, int, int]]) -> dict[str, float]:
    if not events:
        return {
            "note_on_count": 0.0,
            "mean_velocity": 0.0,
            "median_ioi_seconds": 0.0,
            "estimated_bpm": 0.0,
            "duration_seconds": 0.0,
            "note_density_per_second": 0.0,
        }
    times = [item[0] for item in events]
    velocities = [float(item[2]) for item in events]
    ioi = [b - a for a, b in zip(times, times[1:]) if b > a]
    duration = max(0.0, times[-1] - times[0])
    median_ioi = median(ioi) if ioi else 0.0
    bpm = (60.0 / median_ioi) if median_ioi > 0 else 0.0
    density = (len(events) / duration) if duration > 0 else float(len(events))
    return {
        "note_on_count": float(len(events)),
        "mean_velocity": round(mean(velocities), 6),
        "median_ioi_seconds": round(float(median_ioi), 6),
        "estimated_bpm": round(float(bpm), 6),
        "duration_seconds": round(float(duration), 6),
        "note_density_per_second": round(float(density), 6),
    }


def harmony_features_from_events(events: list[tuple[float, int, int]]) -> dict[str, object]:
    if not events:
        return {
            "note_on_count": 0,
            "unique_pitch_classes": 0,
            "pitch_class_histogram": [0] * 12,
            "estimated_key": "unknown",
            "estimated_mode": "unknown",
            "triad_match_score": 0.0,
        }
    pcs = [note % 12 for _, note, _ in events]
    histogram = [0] * 12
    for pc in pcs:
        histogram[pc] += 1
    tonic = max(range(12), key=lambda idx: histogram[idx])
    major_third = histogram[(tonic + 4) % 12]
    minor_third = histogram[(tonic + 3) % 12]
    perfect_fifth = histogram[(tonic + 7) % 12]
    mode = "major" if major_third >= minor_third else "minor"
    triad_strength = (major_third if mode == "major" else minor_third) + perfect_fifth
    note_count = max(1, len(events))
    score = triad_strength / note_count
    key_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    return {
        "note_on_count": len(events),
        "unique_pitch_classes": len({pc for pc in pcs}),
        "pitch_class_histogram": histogram,
        "estimated_key": key_names[tonic],
        "estimated_mode": mode,
        "triad_match_score": round(float(score), 6),
    }
