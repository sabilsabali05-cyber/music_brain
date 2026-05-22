from __future__ import annotations

import argparse
from pathlib import Path
from statistics import mean, pstdev
import sys
from typing import Any

from mido import MidiFile, tick2second

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.feature_dataset_common import load_json, now_iso, save_json
from scripts.trust_common import resolve_performance_context, trust_dir


def _safe_float(value: object, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:  # noqa: BLE001
        return fallback


def _window_duration_seconds(window: dict[str, object]) -> float:
    start = _safe_float(window.get("core_start_seconds"), _safe_float(window.get("global_start_seconds"), 0.0))
    end = _safe_float(window.get("core_end_seconds"), _safe_float(window.get("global_end_seconds"), start))
    return max(0.0, end - start)


def _parse_midi_metrics(midi_path: Path) -> dict[str, object]:
    midi = MidiFile(str(midi_path))
    note_on_times: list[float] = []
    note_durations: list[float] = []
    velocities: list[int] = []
    active_notes: dict[tuple[int, int], list[float]] = {}
    absolute_end = 0.0

    for track in midi.tracks:
        absolute_seconds = 0.0
        tempo = 500000
        for message in track:
            absolute_seconds += tick2second(message.time, midi.ticks_per_beat, tempo)
            absolute_end = max(absolute_end, absolute_seconds)
            if message.type == "set_tempo":
                tempo = int(getattr(message, "tempo", tempo))
                continue
            if message.type == "note_on" and int(getattr(message, "velocity", 0)) > 0:
                key = (int(getattr(message, "channel", 0)), int(message.note))
                active_notes.setdefault(key, []).append(absolute_seconds)
                note_on_times.append(absolute_seconds)
                velocities.append(int(getattr(message, "velocity", 0)))
            elif message.type in {"note_off", "note_on"}:
                velocity = int(getattr(message, "velocity", 0))
                if message.type == "note_on" and velocity > 0:
                    continue
                key = (int(getattr(message, "channel", 0)), int(message.note))
                starts = active_notes.get(key, [])
                if starts:
                    started = starts.pop(0)
                    note_durations.append(max(0.0, absolute_seconds - started))
                    if not starts:
                        active_notes.pop(key, None)

    note_on_times.sort()
    note_count = len(note_on_times)
    density_duration = max(0.001, absolute_end)
    note_on_density = note_count / density_duration
    velocity_mean = mean(velocities) if velocities else 0.0
    velocity_std = pstdev(velocities) if len(velocities) > 1 else 0.0
    avg_note_duration = mean(note_durations) if note_durations else 0.0
    close_pairs = 0
    if len(note_on_times) > 1:
        close_pairs = sum(1 for a, b in zip(note_on_times, note_on_times[1:]) if (b - a) <= 0.06)
    polyphonic_density = close_pairs / max(1, note_count - 1)

    silence_proxy = 1.0
    if note_on_times:
        gaps = [b - a for a, b in zip(note_on_times, note_on_times[1:]) if b > a]
        if gaps:
            long_gaps = sum(1 for gap in gaps if gap >= 0.5)
            silence_proxy = long_gaps / len(gaps)
        else:
            silence_proxy = 0.0

    return {
        "midi_parse_success": True,
        "note_on_count": note_count,
        "note_on_density_per_second": round(float(note_on_density), 6),
        "average_note_duration_seconds": round(float(avg_note_duration), 6),
        "polyphonic_density": round(float(polyphonic_density), 6),
        "velocity_mean": round(float(velocity_mean), 6),
        "velocity_std": round(float(velocity_std), 6),
        "silence_ratio_proxy": round(float(silence_proxy), 6),
    }


def _score_window(window: dict[str, object]) -> tuple[float, list[str], list[str]]:
    reasons: list[str] = []
    warnings: list[str] = []
    status = str(window.get("status", "pending"))
    midi_exists = bool(window.get("midi_exists", False))
    parse_success = bool(window.get("midi_parse_success", False))
    note_count = int(window.get("note_on_count", 0) or 0)
    density = _safe_float(window.get("note_on_density_per_second"), 0.0)
    silence_proxy = _safe_float(window.get("silence_ratio_proxy"), 1.0)

    if status != "success":
        return 0.0, [f"window status={status}"], ["transcription not successful"]
    if not midi_exists:
        return 0.0, ["midi file missing"], ["no MIDI artifact"]
    if not parse_success:
        return 0.1, ["MIDI parse failed"], ["invalid or unreadable MIDI"]

    score = 0.45
    reasons.append("successful transcription window with parseable MIDI")
    if note_count >= 12:
        score += 0.2
        reasons.append("sufficient note-on events")
    elif note_count >= 4:
        score += 0.1
        reasons.append("minimal note-on events available")
    else:
        warnings.append("very low note count")

    if 0.4 <= density <= 15.0:
        score += 0.15
        reasons.append("note density within expected musical range")
    else:
        warnings.append("unusual note density")

    if silence_proxy <= 0.75:
        score += 0.1
    else:
        warnings.append("high silence ratio proxy")

    file_size = int(window.get("midi_file_size_bytes", 0) or 0)
    if file_size >= 256:
        score += 0.1
    else:
        warnings.append("tiny MIDI file")

    return min(1.0, max(0.0, score)), reasons, warnings


def _tier(score: float, status: str, midi_exists: bool, parse_success: bool) -> str:
    if status != "success":
        return "failed"
    if not midi_exists:
        return "missing"
    if not parse_success:
        return "failed"
    if score >= 0.8:
        return "high"
    if score >= 0.55:
        return "medium"
    return "low"


def compute_transcription_reliability(performance_manifest_path: Path) -> Path:
    ctx = resolve_performance_context(performance_manifest_path)
    segments_manifest = load_json(ctx["segments_manifest_path"])
    windows = segments_manifest.get("transcription_windows", [])
    if not isinstance(windows, list):
        windows = []

    merge_report_path = ctx["segments_manifest_path"].parent / "merged" / "merge_report.json"
    merge_report = load_json(merge_report_path) if merge_report_path.exists() else {}
    merge_trim_loss = merge_report.get("events_discarded_context")

    output_windows: list[dict[str, object]] = []
    for raw_window in windows:
        if not isinstance(raw_window, dict):
            continue
        window_id = str(raw_window.get("window_id", "unknown"))
        status = str(raw_window.get("status", "pending"))
        midi_path_value = str(raw_window.get("midi_path") or "").strip()
        midi_path = Path(midi_path_value) if midi_path_value else None
        midi_exists = bool(midi_path and midi_path.exists())
        parse_success = False
        metrics: dict[str, object] = {}
        error_messages: list[str] = []
        midi_size = int(midi_path.stat().st_size) if midi_exists and midi_path is not None else 0
        if midi_exists and midi_path is not None:
            try:
                metrics = _parse_midi_metrics(midi_path)
                parse_success = bool(metrics.get("midi_parse_success", False))
            except Exception as exc:  # noqa: BLE001
                parse_success = False
                error_messages.append(f"midi_parse_error={exc.__class__.__name__}: {exc}")

        window_payload: dict[str, object] = {
            "window_id": window_id,
            "status": status,
            "midi_path": midi_path.resolve().as_posix() if midi_exists and midi_path is not None else midi_path_value or None,
            "midi_exists": midi_exists,
            "midi_parse_success": parse_success,
            "midi_file_size_bytes": midi_size,
            "window_duration_seconds": round(_window_duration_seconds(raw_window), 6),
            "context_trim_loss": merge_trim_loss,
            "error_messages": error_messages,
        }
        window_payload.update(metrics)
        score, reasons, warnings = _score_window(window_payload)
        tier = _tier(score, status, midi_exists, parse_success)
        training_weight = {
            "high": 1.0,
            "medium": 0.7,
            "low": 0.35,
            "failed": 0.0,
            "missing": 0.0,
        }.get(tier, 0.0)
        window_payload["transcription_reliability_score"] = round(float(score), 6)
        window_payload["reliability_tier"] = tier
        window_payload["reasons"] = reasons
        window_payload["warnings"] = warnings
        window_payload["recommended_training_weight"] = training_weight
        output_windows.append(window_payload)

    counts = {"high_windows": 0, "medium_windows": 0, "low_windows": 0, "failed_windows": 0, "missing_windows": 0}
    for item in output_windows:
        tier = str(item.get("reliability_tier", "low"))
        key = f"{tier}_windows"
        if key in counts:
            counts[key] += 1
    mean_score = mean([float(item.get("transcription_reliability_score", 0.0) or 0.0) for item in output_windows]) if output_windows else 0.0
    mean_weight = mean([float(item.get("recommended_training_weight", 0.0) or 0.0) for item in output_windows]) if output_windows else 0.0

    payload = {
        "performance_id": ctx["performance_id"],
        "segment_run_id": ctx["segment_run_id"],
        "created_at": now_iso(),
        "source_artifacts": {
            "performance_manifest_path": ctx["performance_manifest_path"].as_posix(),
            "segments_manifest_path": ctx["segments_manifest_path"].as_posix(),
            "merge_report_path": merge_report_path.resolve().as_posix() if merge_report_path.exists() else None,
        },
        "windows": output_windows,
        "summary": {
            **counts,
            "window_count": len(output_windows),
            "mean_reliability_score": round(float(mean_score), 6),
            "training_weight_mean": round(float(mean_weight), 6),
        },
    }
    out_path = trust_dir(ctx["feature_dir"]) / "transcription_reliability.json"
    save_json(out_path, payload)
    return out_path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute per-window transcription reliability for active performance run.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    args = parser.parse_args()
    output_path = compute_transcription_reliability(Path(args.performance_manifest))
    print(f"TRANSCRIPTION_RELIABILITY_PATH={output_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
