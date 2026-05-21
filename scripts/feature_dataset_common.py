from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median, pstdev

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


def _coerce_float(value: object, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:  # noqa: BLE001
        return fallback


def _window_core_bounds(window: dict[str, object]) -> tuple[float, float]:
    core_start = _coerce_float(window.get("core_start_seconds"), _coerce_float(window.get("global_start_seconds"), 0.0))
    core_end = _coerce_float(window.get("core_end_seconds"), _coerce_float(window.get("global_end_seconds"), core_start))
    return core_start, max(core_start, core_end)


def successful_windows_with_midi(segments_manifest: dict[str, object]) -> list[dict[str, object]]:
    windows = segments_manifest.get("transcription_windows", [])
    if not isinstance(windows, list):
        return []
    selected: list[dict[str, object]] = []
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
        selected.append(window)
    return selected


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


def window_core_events_global(window: dict[str, object]) -> list[tuple[float, int, int]]:
    midi_value = str(window.get("midi_path") or "").strip()
    if not midi_value:
        return []
    midi_path = Path(midi_value)
    if not midi_path.exists():
        return []
    local_events = midi_note_events(midi_path)
    core_start, core_end = _window_core_bounds(window)
    core_duration = max(0.0, core_end - core_start)
    pre_context = _coerce_float(window.get("pre_context_seconds"), 0.0)
    local_core_start = pre_context
    local_core_end = pre_context + core_duration if core_duration > 0 else float("inf")
    output: list[tuple[float, int, int]] = []
    for local_time, note, velocity in local_events:
        if local_time < local_core_start or local_time > local_core_end:
            continue
        mapped = core_start + (local_time - local_core_start)
        output.append((mapped, note, velocity))
    output.sort(key=lambda item: item[0])
    return output


def collect_global_events(
    *,
    segments_manifest: dict[str, object],
    merged_midi_path: Path | None,
) -> tuple[list[tuple[float, int, int]], str, list[str]]:
    limitations: list[str] = []
    if merged_midi_path and merged_midi_path.exists():
        return midi_note_events(merged_midi_path), "merged", limitations

    windows = successful_windows_with_midi(segments_manifest)
    events: list[tuple[float, int, int]] = []
    for window in windows:
        events.extend(window_core_events_global(window))
    events.sort(key=lambda item: item[0])
    if events:
        limitations.append("merged MIDI unavailable; built global timeline from successful window core MIDI.")
        return events, "window_fallback", limitations
    limitations.append("no global MIDI timeline could be constructed from merged or window sources.")
    return [], "no_midi", limitations


def events_in_range(
    events: list[tuple[float, int, int]],
    *,
    start_seconds: float,
    end_seconds: float,
) -> list[tuple[float, int, int]]:
    if end_seconds <= start_seconds:
        return []
    return [item for item in events if start_seconds <= item[0] <= end_seconds]


def build_time_bins(start_seconds: float, end_seconds: float, *, bin_seconds: float) -> list[tuple[float, float]]:
    if end_seconds <= start_seconds:
        return []
    size = max(0.5, float(bin_seconds))
    output: list[tuple[float, float]] = []
    cursor = start_seconds
    while cursor < end_seconds:
        nxt = min(end_seconds, cursor + size)
        output.append((cursor, nxt))
        cursor = nxt
    return output


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


def rhythm_feature_vector(
    events: list[tuple[float, int, int]],
    *,
    start_seconds: float,
    end_seconds: float,
) -> dict[str, object]:
    duration = max(0.0, end_seconds - start_seconds)
    local = events_in_range(events, start_seconds=start_seconds, end_seconds=end_seconds)
    if not local:
        return {
            "note_on_count": 0,
            "note_on_density_per_second": 0.0,
            "average_velocity": 0.0,
            "velocity_accent_stats": {"mean": 0.0, "std": 0.0, "accent_ratio": 0.0},
            "silence_ratio": 1.0,
            "polyphonic_density": 0.0,
            "inter_onset_interval_histogram": {},
            "common_ioi_seconds": [],
            "common_ioi_ratios": [],
            "estimated_pulse_seconds": 0.0,
            "estimated_grid_resolution_seconds": 0.0,
            "syncopation_proxy_score": 0.0,
            "repetition_proxy_score": 0.0,
            "burst_density_regions": [],
            "sparse_regions": [],
            "pitch_class_activity": [0] * 12,
        }

    times = [item[0] for item in local]
    notes = [item[1] for item in local]
    velocities = [float(item[2]) for item in local]
    note_count = len(local)
    density = note_count / duration if duration > 0 else float(note_count)
    mean_vel = mean(velocities)
    std_vel = pstdev(velocities) if len(velocities) > 1 else 0.0
    accent_threshold = mean_vel + std_vel
    accent_ratio = sum(1 for value in velocities if value >= accent_threshold) / max(1, len(velocities))

    ioi = [b - a for a, b in zip(times, times[1:]) if b > a]
    rounded_ioi = [round(value, 2) for value in ioi]
    histogram: dict[str, int] = {}
    for value in rounded_ioi:
        key = f"{value:.2f}"
        histogram[key] = histogram.get(key, 0) + 1
    common_ioi = sorted(histogram.items(), key=lambda item: item[1], reverse=True)[:3]
    common_ioi_seconds = [float(key) for key, _ in common_ioi]
    pulse = median(ioi) if ioi else 0.0
    grid = pulse / 2.0 if pulse > 0 else 0.0
    ratios = [round(value / pulse, 3) for value in common_ioi_seconds if pulse > 0 and value > 0]
    repetition = 0.0
    if rounded_ioi:
        repetition = max(histogram.values()) / len(rounded_ioi)

    bins = build_time_bins(start_seconds, end_seconds, bin_seconds=4.0)
    region_density: list[tuple[tuple[float, float], float]] = []
    for bin_start, bin_end in bins:
        region_events = events_in_range(local, start_seconds=bin_start, end_seconds=bin_end)
        span = max(0.001, bin_end - bin_start)
        region_density.append(((bin_start, bin_end), len(region_events) / span))
    burst = sorted(region_density, key=lambda item: item[1], reverse=True)[:3]
    sparse = sorted(region_density, key=lambda item: item[1])[:3]

    silence_ratio = 0.0
    if bins:
        silent_bins = sum(1 for (bin_start, bin_end), _ in region_density if not events_in_range(local, start_seconds=bin_start, end_seconds=bin_end))
        silence_ratio = silent_bins / len(bins)

    polyphony = 0.0
    if note_count > 1:
        close_pairs = sum(1 for a, b in zip(times, times[1:]) if (b - a) <= 0.08)
        polyphony = close_pairs / (note_count - 1)

    syncopation = 0.0
    if pulse > 0:
        phases = [((time - start_seconds) % pulse) / pulse for time in times]
        syncopation = float(mean(abs(phase - round(phase)) for phase in phases))

    pitch_class_activity = [0] * 12
    for note in notes:
        pitch_class_activity[note % 12] += 1

    return {
        "note_on_count": note_count,
        "note_on_density_per_second": round(density, 6),
        "average_velocity": round(mean_vel, 6),
        "velocity_accent_stats": {
            "mean": round(mean_vel, 6),
            "std": round(std_vel, 6),
            "accent_ratio": round(accent_ratio, 6),
        },
        "silence_ratio": round(silence_ratio, 6),
        "polyphonic_density": round(polyphony, 6),
        "inter_onset_interval_histogram": histogram,
        "common_ioi_seconds": common_ioi_seconds,
        "common_ioi_ratios": ratios,
        "estimated_pulse_seconds": round(float(pulse), 6),
        "estimated_grid_resolution_seconds": round(float(grid), 6),
        "syncopation_proxy_score": round(syncopation, 6),
        "repetition_proxy_score": round(repetition, 6),
        "burst_density_regions": [
            {"start_seconds": round(item[0][0], 6), "end_seconds": round(item[0][1], 6), "density": round(item[1], 6)}
            for item in burst
        ],
        "sparse_regions": [
            {"start_seconds": round(item[0][0], 6), "end_seconds": round(item[0][1], 6), "density": round(item[1], 6)}
            for item in sparse
        ],
        "pitch_class_activity": pitch_class_activity,
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


def _key_candidates_from_histogram(histogram: list[int]) -> list[dict[str, object]]:
    key_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    total = max(1, sum(histogram))
    ranked = sorted([(index, value / total) for index, value in enumerate(histogram)], key=lambda item: item[1], reverse=True)[:3]
    return [{"key": key_names[index], "score": round(score, 6)} for index, score in ranked]


def _chord_candidate(histogram: list[int]) -> tuple[str, str, int, float]:
    key_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    total = max(1, sum(histogram))
    best_label = "N"
    best_quality = "unknown"
    best_root = 0
    best_score = 0.0
    for root in range(12):
        major = histogram[root] + histogram[(root + 4) % 12] + histogram[(root + 7) % 12]
        minor = histogram[root] + histogram[(root + 3) % 12] + histogram[(root + 7) % 12]
        if major >= minor and major > best_score:
            best_score = float(major)
            best_label = f"{key_names[root]}:maj"
            best_quality = "major"
            best_root = root
        if minor > major and minor > best_score:
            best_score = float(minor)
            best_label = f"{key_names[root]}:min"
            best_quality = "minor"
            best_root = root
    return best_label, best_quality, best_root, round(best_score / total, 6)


def harmony_feature_vector(
    events: list[tuple[float, int, int]],
    *,
    start_seconds: float,
    end_seconds: float,
    bin_seconds: float = 4.0,
) -> dict[str, object]:
    local = events_in_range(events, start_seconds=start_seconds, end_seconds=end_seconds)
    duration = max(0.0, end_seconds - start_seconds)
    if not local:
        return {
            "pitch_class_histogram": [0] * 12,
            "bass_pitch_class_histogram": [0] * 12,
            "estimated_key_candidates": [],
            "chord_candidates": [],
            "chord_timeline": [],
            "chord_change_count": 0,
            "harmonic_rhythm_seconds_per_change": 0.0,
            "root_motion_intervals": [],
            "repeated_chord_score": 0.0,
            "stepwise_root_motion_score": 0.0,
            "chromatic_motion_score": 0.0,
            "circle_motion_score": 0.0,
            "pedal_tone_candidates": [],
            "no_chord_regions": [{"start_seconds": round(start_seconds, 6), "end_seconds": round(end_seconds, 6)}] if duration > 0 else [],
        }

    pitch_hist = [0] * 12
    bass_hist = [0] * 12
    for _, note, _ in local:
        pitch_hist[note % 12] += 1
    key_candidates = _key_candidates_from_histogram(pitch_hist)

    bins = build_time_bins(start_seconds, end_seconds, bin_seconds=bin_seconds)
    chord_timeline: list[dict[str, object]] = []
    no_chord_regions: list[dict[str, float]] = []
    roots: list[int] = []
    for bin_start, bin_end in bins:
        region = events_in_range(local, start_seconds=bin_start, end_seconds=bin_end)
        if not region:
            no_chord_regions.append({"start_seconds": round(bin_start, 6), "end_seconds": round(bin_end, 6)})
            continue
        region_hist = [0] * 12
        min_note = min(note for _, note, _ in region)
        bass_hist[min_note % 12] += 1
        for _, note, _ in region:
            region_hist[note % 12] += 1
        label, quality, root, confidence = _chord_candidate(region_hist)
        chord_timeline.append(
            {
                "start_seconds": round(bin_start, 6),
                "end_seconds": round(bin_end, 6),
                "chord_label_candidate": label,
                "chord_quality_candidate": quality,
                "active_pitch_classes": [index for index, value in enumerate(region_hist) if value > 0],
                "bass_pitch_class": int(min_note % 12),
                "confidence": confidence,
                "evidence": {"pitch_class_histogram": region_hist},
            }
        )
        roots.append(root)

    chord_candidates = [item["chord_label_candidate"] for item in chord_timeline[:6]]
    change_count = sum(1 for a, b in zip(roots, roots[1:]) if a != b)
    harmonic_rhythm = duration / max(1, change_count) if duration > 0 else 0.0
    intervals = [((b - a) % 12) for a, b in zip(roots, roots[1:])]
    repeated = sum(1 for value in intervals if value == 0) / max(1, len(intervals))
    stepwise = sum(1 for value in intervals if value in {1, 11, 2, 10}) / max(1, len(intervals))
    chromatic = sum(1 for value in intervals if value in {1, 11}) / max(1, len(intervals))
    circle = sum(1 for value in intervals if value in {5, 7}) / max(1, len(intervals))
    pedal_candidates = []
    total_bass = sum(bass_hist)
    if total_bass > 0:
        dominant_pc = max(range(12), key=lambda idx: bass_hist[idx])
        dominance = bass_hist[dominant_pc] / total_bass
        if dominance >= 0.5:
            pedal_candidates.append({"bass_pitch_class": dominant_pc, "dominance": round(dominance, 6)})

    return {
        "pitch_class_histogram": pitch_hist,
        "bass_pitch_class_histogram": bass_hist,
        "estimated_key_candidates": key_candidates,
        "chord_candidates": chord_candidates,
        "chord_timeline": chord_timeline,
        "chord_change_count": change_count,
        "harmonic_rhythm_seconds_per_change": round(float(harmonic_rhythm), 6),
        "root_motion_intervals": intervals,
        "repeated_chord_score": round(float(repeated), 6),
        "stepwise_root_motion_score": round(float(stepwise), 6),
        "chromatic_motion_score": round(float(chromatic), 6),
        "circle_motion_score": round(float(circle), 6),
        "pedal_tone_candidates": pedal_candidates,
        "no_chord_regions": no_chord_regions,
    }
