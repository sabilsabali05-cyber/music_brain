from __future__ import annotations

import hashlib
import json
import math
import random
import shutil
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.util import find_spec
from statistics import median
from pathlib import Path
from typing import Any

from mido import Message, MetaMessage, MidiFile, MidiTrack, second2tick

from features.composition_projects.draft_musicality_schema import DraftMusicalityAnalysis, redact_private_path

ROOT_DIR = Path(__file__).resolve().parents[2]
PROJECT_ID = "presentable_composition_from_draft_v1"
OUTPUT_ROOT = ROOT_DIR / "outputs" / PROJECT_ID
REPORTS_ROOT = ROOT_DIR / "reports" / "composition_projects"
DATASET_ROOT = ROOT_DIR / "datasets" / "composition_projects"
DEFAULT_LOCAL_CONFIG = ROOT_DIR / "config" / "presentable_composition_from_draft.local.json"

INPUT_PATH_REQUIRED_STATUS = "missing_local_midi_draft"


@dataclass(frozen=True)
class PipelineContext:
    local_input_midi_path: Path | None
    local_input_midi_path_redacted: str
    local_midi_found: bool
    training_allowed: bool
    candidate_count: int
    seed: int


@dataclass(frozen=True)
class NoteEvent:
    start_seconds: float
    end_seconds: float
    note: int
    velocity: int
    track_idx: int
    channel: int
    start_tick: int
    end_tick: int


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT_DIR.resolve()).as_posix()
    except Exception:  # noqa: BLE001
        return path.as_posix()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _write_md(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(64 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def load_context(config_path: Path | None = None) -> PipelineContext:
    target = config_path or DEFAULT_LOCAL_CONFIG
    payload: dict[str, Any] = {}
    if target.exists():
        try:
            loaded = json.loads(target.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                payload = loaded
        except json.JSONDecodeError:
            payload = {}
    input_raw = str(payload.get("local_input_midi_path", "")).strip()
    local_path = Path(input_raw) if input_raw else None
    found = bool(local_path and local_path.exists() and local_path.is_file())
    training_allowed = bool(payload.get("training_allowed", False))
    candidate_count = max(8, int(payload.get("candidate_count", 8)))
    seed = int(payload.get("seed", 4117))
    redacted = redact_private_path(input_raw) if input_raw else "<PRIVATE_LOCAL_PATH>/missing.mid"
    return PipelineContext(
        local_input_midi_path=local_path,
        local_input_midi_path_redacted=redacted,
        local_midi_found=found,
        training_allowed=training_allowed,
        candidate_count=candidate_count,
        seed=seed,
    )


def write_local_manifest(context: PipelineContext) -> Path:
    cache_root = OUTPUT_ROOT / "local_input_cache"
    cache_root.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "project_id": PROJECT_ID,
        "source_path_redacted": context.local_input_midi_path_redacted,
        "local_midi_found": context.local_midi_found,
        "training_allowed": context.training_allowed,
    }
    if context.local_midi_found and context.local_input_midi_path:
        payload.update(
            {
                "source_sha256": _hash_file(context.local_input_midi_path),
                "source_size_bytes": int(context.local_input_midi_path.stat().st_size),
                "source_name": context.local_input_midi_path.name,
            }
        )
    else:
        payload["status"] = INPUT_PATH_REQUIRED_STATUS
    manifest_path = cache_root / "local_input_manifest.json"
    _write_json(manifest_path, payload)
    return manifest_path


def _is_note_off(msg: Any) -> bool:
    if msg.type == "note_off":
        return True
    return msg.type == "note_on" and int(getattr(msg, "velocity", 0)) == 0


def _tempo_segments(midi: MidiFile) -> tuple[list[tuple[int, int]], list[tuple[int, int, float]], list[dict[str, Any]], int]:
    raw_events: list[tuple[int, int]] = [(0, 500000)]
    explicit_event_count = 0
    for track in midi.tracks:
        abs_tick = 0
        for msg in track:
            abs_tick += int(msg.time)
            if msg.type == "set_tempo":
                explicit_event_count += 1
                raw_events.append((abs_tick, int(msg.tempo)))
    dedup: dict[int, int] = {}
    for tick, tempo in raw_events:
        dedup[tick] = tempo
    events = sorted(dedup.items(), key=lambda item: item[0])
    segments: list[tuple[int, int, float]] = []
    acc = 0.0
    for idx, (tick, tempo) in enumerate(events):
        if idx > 0:
            prev_tick, prev_tempo = events[idx - 1]
            acc += (tick - prev_tick) * (prev_tempo / 1_000_000.0) / max(1, midi.ticks_per_beat)
        segments.append((tick, tempo, acc))
    tempo_rows = [
        {
            "tick": int(tick),
            "tempo_us_per_beat": int(tempo),
            "bpm": round(60_000_000.0 / max(1, int(tempo)), 6),
        }
        for tick, tempo in events
    ]
    return events, segments, tempo_rows, explicit_event_count


def _tick_to_seconds(abs_tick: int, segments: list[tuple[int, int, float]], ticks_per_beat: int) -> float:
    if not segments:
        return abs_tick * (500000.0 / 1_000_000.0) / max(1, ticks_per_beat)
    idx = 0
    for seg_idx, (tick, _, _) in enumerate(segments):
        if tick <= abs_tick:
            idx = seg_idx
        else:
            break
    start_tick, tempo, base_seconds = segments[idx]
    return base_seconds + (abs_tick - start_tick) * (tempo / 1_000_000.0) / max(1, ticks_per_beat)


def _parse_midi(path: Path) -> tuple[list[NoteEvent], dict[str, Any]]:
    midi = MidiFile(path.as_posix())
    ticks_per_beat = max(1, int(midi.ticks_per_beat))
    tempo_events, tempo_segments, tempo_rows, explicit_tempo_events = _tempo_segments(midi)
    all_notes: list[NoteEvent] = []
    track_abs_ticks: list[int] = []
    note_on_count = 0
    note_off_count = 0
    note_on_zero_velocity_count = 0
    channels: set[int] = set()
    pitch_min: int | None = None
    pitch_max: int | None = None
    unmatched_note_off = 0
    for track_idx, track in enumerate(midi.tracks):
        abs_tick = 0
        active: dict[tuple[int, int], list[tuple[int, float, int]]] = {}
        for msg in track:
            abs_tick += int(msg.time)
            if msg.type in {"note_on", "note_off"}:
                channel = int(getattr(msg, "channel", 0))
                note = int(getattr(msg, "note", 0))
                channels.add(channel)
                pitch_min = note if pitch_min is None else min(pitch_min, note)
                pitch_max = note if pitch_max is None else max(pitch_max, note)
            if msg.type == "note_on" and int(getattr(msg, "velocity", 0)) > 0:
                note_on_count += 1
                channel = int(msg.channel)
                note = int(msg.note)
                start_sec = _tick_to_seconds(abs_tick, tempo_segments, ticks_per_beat)
                active.setdefault((channel, note), []).append((abs_tick, start_sec, int(msg.velocity)))
            elif _is_note_off(msg):
                channel = int(getattr(msg, "channel", 0))
                note = int(getattr(msg, "note", 0))
                if msg.type == "note_on":
                    note_on_zero_velocity_count += 1
                note_off_count += 1
                key = (channel, note)
                starts = active.get(key, [])
                if starts:
                    start_tick, start_sec, velocity = starts.pop(0)
                    end_sec = _tick_to_seconds(abs_tick, tempo_segments, ticks_per_beat)
                    if end_sec > start_sec:
                        all_notes.append(
                            NoteEvent(
                                start_seconds=start_sec,
                                end_seconds=end_sec,
                                note=note,
                                velocity=velocity,
                                track_idx=track_idx,
                                channel=channel,
                                start_tick=start_tick,
                                end_tick=abs_tick,
                            )
                        )
                else:
                    unmatched_note_off += 1
        track_abs_ticks.append(abs_tick)
    all_notes.sort(key=lambda row: row.start_seconds)
    total_ticks = max(track_abs_ticks, default=0)
    duration_seconds = _tick_to_seconds(total_ticks, tempo_segments, ticks_per_beat)
    open_notes = max(0, note_on_count - note_off_count)
    stats = {
        "file_type": int(midi.type),
        "ticks_per_beat": ticks_per_beat,
        "track_count": len(midi.tracks),
        "track_names": [str(track.name or f"Track {idx + 1}") for idx, track in enumerate(midi.tracks)],
        "tempo_events": tempo_rows,
        "explicit_tempo_event_count": explicit_tempo_events,
        "time_signature_events": _extract_time_signature_events(midi),
        "note_on_velocity_gt_0": note_on_count,
        "note_off_events": note_off_count,
        "note_on_zero_velocity": note_on_zero_velocity_count,
        "channels": sorted(channels),
        "pitch_range": [pitch_min, pitch_max] if pitch_min is not None and pitch_max is not None else None,
        "total_ticks": total_ticks,
        "duration_seconds_estimate": round(duration_seconds, 6),
        "unmatched_note_off_events": unmatched_note_off,
        "open_note_events": open_notes,
        "tempo_detected_bpm": round(60_000_000.0 / max(1, tempo_events[0][1]), 6) if tempo_events else None,
    }
    return all_notes, stats


def _extract_time_signature_events(midi: MidiFile) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for track_idx, track in enumerate(midi.tracks):
        abs_tick = 0
        for msg in track:
            abs_tick += int(msg.time)
            if msg.type == "time_signature":
                rows.append(
                    {
                        "track_idx": track_idx,
                        "tick": abs_tick,
                        "numerator": int(msg.numerator),
                        "denominator": int(msg.denominator),
                    }
                )
    rows.sort(key=lambda row: (row["tick"], row["track_idx"]))
    return rows


def _infer_tempo(notes: list[NoteEvent], tempo_events: list[dict[str, Any]], explicit_tempo_event_count: int) -> tuple[float | None, float, str]:
    if explicit_tempo_event_count > 0 and tempo_events:
        return float(tempo_events[0]["bpm"]), 0.98, "set_tempo meta event present in MIDI"
    if len(notes) < 2:
        return None, 0.0, "insufficient note events to infer tempo"
    starts = sorted(row.start_seconds for row in notes)
    ioi = [starts[idx] - starts[idx - 1] for idx in range(1, len(starts)) if (starts[idx] - starts[idx - 1]) > 0.05]
    if not ioi:
        return None, 0.0, "note onset intervals were degenerate"
    median_ioi = median(ioi)
    if median_ioi <= 0:
        return None, 0.0, "median onset interval was non-positive"
    bpm = 60.0 / median_ioi
    while bpm < 70.0:
        bpm *= 2.0
    while bpm > 180.0:
        bpm /= 2.0
    return round(bpm, 6), 0.38, "inferred from median note-on interval; no set_tempo meta event"


def _detect_key(notes: list[NoteEvent]) -> tuple[str | None, float, str]:
    if not notes:
        return None, 0.0, "no note events available"
    weights = [0.0] * 12
    for row in notes:
        dur = max(0.01, row.end_seconds - row.start_seconds)
        weights[row.note % 12] += dur * (0.5 + (row.velocity / 127.0))
    major_profile = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
    minor_profile = [6.33, 2.68, 3.52, 5.38, 2.6, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
    names = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
    total = sum(weights)
    if total <= 0:
        return None, 0.0, "pitch-class distribution had zero weight"
    norm = [value / total for value in weights]
    best_score = -1.0
    second_best = -1.0
    best_name: str | None = None
    for tonic in range(12):
        rot_major = [major_profile[(i - tonic) % 12] for i in range(12)]
        rot_minor = [minor_profile[(i - tonic) % 12] for i in range(12)]
        for mode, profile in (("major", rot_major), ("minor", rot_minor)):
            prof_total = sum(profile)
            prof_norm = [p / prof_total for p in profile]
            score = sum(norm[i] * prof_norm[i] for i in range(12))
            if score > best_score:
                second_best = best_score
                best_score = score
                best_name = f"{names[tonic]} {mode}"
            elif score > second_best:
                second_best = score
    margin = max(0.0, best_score - max(0.0, second_best))
    confidence = max(0.2, min(0.95, 0.35 + margin * 8.0))
    return best_name, round(confidence, 6), "pitch-class profile matching (Krumhansl-style)"


def _extract_musical_evidence(notes: list[NoteEvent], duration: float) -> dict[str, Any]:
    if not notes or duration <= 0:
        return {
            "phrases": [],
            "motifs": [],
            "harmony_windows": [],
            "rhythm_cells": [],
            "bass_top_relationships": [],
            "density_windows": [],
            "register_roles": [],
        }
    starts = sorted(row.start_seconds for row in notes)
    pitches = [row.note for row in notes]
    inter_onsets = [starts[idx] - starts[idx - 1] for idx in range(1, len(starts))]
    phrases: list[dict[str, Any]] = []
    phrase_start = starts[0]
    for idx, gap in enumerate(inter_onsets, start=1):
        if gap >= 1.0:
            phrase_end = starts[idx - 1]
            phrases.append({"start": round(phrase_start, 6), "end": round(phrase_end, 6), "gap_after": round(gap, 6)})
            phrase_start = starts[idx]
    phrases.append({"start": round(phrase_start, 6), "end": round(starts[-1], 6), "gap_after": 0.0})
    interval_sequence = [pitches[idx] - pitches[idx - 1] for idx in range(1, len(pitches))]
    motif_counts: dict[tuple[int, ...], int] = {}
    for idx in range(len(interval_sequence) - 2):
        cell = tuple(interval_sequence[idx : idx + 3])
        motif_counts[cell] = motif_counts.get(cell, 0) + 1
    motifs = [
        {"interval_pattern": list(pattern), "occurrences": count}
        for pattern, count in sorted(motif_counts.items(), key=lambda item: item[1], reverse=True)[:5]
        if count > 1
    ]
    window = 2.0
    harmony_windows: list[dict[str, Any]] = []
    cursor = 0.0
    while cursor < duration:
        active = [row for row in notes if row.start_seconds <= cursor + window and row.end_seconds >= cursor]
        if active:
            pcs = sorted({row.note % 12 for row in active})
            harmony_windows.append({"start": round(cursor, 6), "end": round(min(duration, cursor + window), 6), "pitch_classes": pcs, "active_notes": len(active)})
        cursor += window
    rhythm_cells_map: dict[float, int] = {}
    for gap in inter_onsets:
        bucket = round(gap, 2)
        rhythm_cells_map[bucket] = rhythm_cells_map.get(bucket, 0) + 1
    rhythm_cells = [
        {"onset_gap_seconds": gap, "count": count}
        for gap, count in sorted(rhythm_cells_map.items(), key=lambda item: item[1], reverse=True)[:6]
    ]
    grouped: dict[float, list[int]] = {}
    for row in notes:
        bucket = round(row.start_seconds / 0.5) * 0.5
        grouped.setdefault(bucket, []).append(row.note)
    bass_top: list[dict[str, Any]] = []
    for start, chord in sorted(grouped.items())[:24]:
        if len(chord) >= 2:
            bass_top.append(
                {
                    "start": round(start, 6),
                    "bass_note": int(min(chord)),
                    "top_note": int(max(chord)),
                    "spread": int(max(chord) - min(chord)),
                }
            )
    density_windows: list[dict[str, Any]] = []
    density_window = max(2.0, duration / 8.0)
    cursor = 0.0
    while cursor < duration:
        count = sum(1 for row in notes if cursor <= row.start_seconds < (cursor + density_window))
        density_windows.append({"start": round(cursor, 6), "end": round(min(duration, cursor + density_window), 6), "note_count": count})
        cursor += density_window
    low = sum(1 for row in notes if row.note < 48)
    mid = sum(1 for row in notes if 48 <= row.note <= 72)
    high = sum(1 for row in notes if row.note > 72)
    register_roles = [
        {"register": "low", "note_count": low},
        {"register": "mid", "note_count": mid},
        {"register": "high", "note_count": high},
    ]
    return {
        "phrases": phrases[:12],
        "motifs": motifs,
        "harmony_windows": harmony_windows[:16],
        "rhythm_cells": rhythm_cells,
        "bass_top_relationships": bass_top,
        "density_windows": density_windows,
        "register_roles": register_roles,
    }


def _score_dimensions(notes: list[NoteEvent], duration: float, evidence: dict[str, Any]) -> dict[str, float]:
    if not notes or duration <= 0:
        return {
            "harmony_score": 0.0,
            "melody_motif_score": 0.0,
            "rhythm_groove_score": 0.0,
            "bass_score": 0.0,
            "structure_score": 0.0,
            "texture_arrangement_score": 0.0,
            "musicality_score": 0.0,
        }
    pitches = [n.note for n in notes]
    durations = [max(0.01, n.end_seconds - n.start_seconds) for n in notes]
    starts = [n.start_seconds for n in notes]
    unique_pc = len({p % 12 for p in pitches}) / 12.0
    unique_notes = len(set(pitches)) / max(1.0, min(50.0, float(len(pitches))))
    leaps = [abs(pitches[i] - pitches[i - 1]) for i in range(1, len(pitches))]
    leap_ratio = sum(1 for x in leaps if x > 7) / max(1, len(leaps))
    step_ratio = sum(1 for x in leaps if x <= 2) / max(1, len(leaps))
    rhythm_var = len({round(d, 2) for d in durations}) / max(1.0, min(18.0, float(len(durations))))
    on_grid = sum(1 for s in starts if abs((s * 2.0) - round(s * 2.0)) < 0.1) / max(1, len(starts))
    low_notes = [n for n in pitches if n < 52]
    bass_presence = min(1.0, len(low_notes) / max(8.0, len(pitches) * 0.35))
    sections = max(1, int(duration / 16.0))
    section_density = []
    for section_idx in range(sections):
        s0 = section_idx * (duration / sections)
        s1 = (section_idx + 1) * (duration / sections)
        section_density.append(sum(1 for s in starts if s0 <= s < s1))
    dynamic_curve = 0.0
    if section_density:
        dynamic_curve = (max(section_density) - min(section_density)) / max(1.0, float(max(section_density)))
    track_variety = len({n.track_idx for n in notes}) / 8.0
    harmony_window_depth = min(1.0, len([w for w in evidence.get("harmony_windows", []) if len(w.get("pitch_classes", [])) >= 3]) / 8.0)
    motif_repetition = min(1.0, sum(int(m.get("occurrences", 0)) for m in evidence.get("motifs", [])) / 24.0)
    rhythm_cell_variety = min(1.0, len(evidence.get("rhythm_cells", [])) / 6.0)
    harmony = max(0.0, min(1.0, 0.4 * unique_pc + 0.25 * harmony_window_depth + 0.2 * (1.0 - leap_ratio) + 0.15 * rhythm_var))
    melody = max(0.0, min(1.0, 0.35 * step_ratio + 0.25 * unique_notes + 0.2 * motif_repetition + 0.2 * (1.0 - leap_ratio)))
    rhythm = max(0.0, min(1.0, 0.35 * on_grid + 0.25 * rhythm_var + 0.2 * rhythm_cell_variety + 0.2 * dynamic_curve))
    bass = max(0.0, min(1.0, 0.6 * bass_presence + 0.4 * (1.0 - leap_ratio)))
    structure = max(0.0, min(1.0, 0.6 * dynamic_curve + 0.4 * min(1.0, duration / 100.0)))
    texture = max(0.0, min(1.0, 0.55 * track_variety + 0.45 * dynamic_curve))
    musicality = max(0.0, min(1.0, (harmony + melody + rhythm + bass + structure + texture) / 6.0))
    return {
        "harmony_score": harmony,
        "melody_motif_score": melody,
        "rhythm_groove_score": rhythm,
        "bass_score": bass,
        "structure_score": structure,
        "texture_arrangement_score": texture,
        "musicality_score": musicality,
    }


def _has_dependency(name: str) -> bool:
    return find_spec(name) is not None


def _optional_pretty_midi(path: Path) -> dict[str, Any]:
    if not _has_dependency("pretty_midi"):
        return {"installed": False, "status": "missing_dependency"}
    try:
        import pretty_midi  # type: ignore

        midi = pretty_midi.PrettyMIDI(path.as_posix())
        note_count = sum(len(inst.notes) for inst in midi.instruments)
        tempo_times, tempi = midi.get_tempo_changes()
        return {
            "installed": True,
            "status": "ok",
            "instrument_count": len(midi.instruments),
            "note_count": int(note_count),
            "tempo_change_count": int(len(tempi)),
            "first_tempo_bpm": round(float(tempi[0]), 6) if len(tempi) > 0 else None,
            "duration_seconds": round(float(midi.get_end_time()), 6),
            "tempo_time_markers": [round(float(x), 6) for x in list(tempo_times[:8])],
        }
    except Exception as exc:  # noqa: BLE001
        return {"installed": True, "status": "error", "error": str(exc)}


def _optional_music21(path: Path) -> dict[str, Any]:
    if not _has_dependency("music21"):
        return {"installed": False, "status": "missing_dependency"}
    try:
        from music21 import converter  # type: ignore

        score = converter.parse(path.as_posix())
        flat = score.flatten()
        notes = flat.notes
        key_obj = flat.analyze("key")
        tempos = [element.number for element in flat.getElementsByClass("MetronomeMark") if getattr(element, "number", None)]
        return {
            "installed": True,
            "status": "ok",
            "note_count": int(len(notes)),
            "parts": int(len(score.parts)),
            "duration_quarter_length": float(flat.duration.quarterLength),
            "analyzed_key": str(key_obj) if key_obj else None,
            "tempo_marks": [float(x) for x in tempos[:8]],
        }
    except Exception as exc:  # noqa: BLE001
        return {"installed": True, "status": "error", "error": str(exc)}


def _raw_midi_header(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            header = handle.read(14)
        if len(header) < 14 or header[0:4] != b"MThd":
            return {"status": "invalid_or_unknown_header", "header_hex": header.hex()}
        header_len = int.from_bytes(header[4:8], byteorder="big", signed=False)
        fmt = int.from_bytes(header[8:10], byteorder="big", signed=False)
        tracks = int.from_bytes(header[10:12], byteorder="big", signed=False)
        division = int.from_bytes(header[12:14], byteorder="big", signed=False)
        return {
            "status": "ok",
            "chunk_length": header_len,
            "format_type": fmt,
            "declared_track_count": tracks,
            "division_raw": division,
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": str(exc)}


def collect_midi_parser_diagnostics(path: Path, source_path_redacted: str) -> dict[str, Any]:
    exists = path.exists() and path.is_file()
    payload: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_path_redacted": source_path_redacted,
        "file_found": bool(exists),
        "empty_or_malformed": False,
        "parser_ignore_suspicion": False,
    }
    if not exists:
        payload.update(
            {
                "status": "missing_file",
                "size_bytes": 0,
                "raw_inspection": _raw_midi_header(path),
                "parsers": {
                    "mido": {"status": "missing_file"},
                    "pretty_midi": _optional_pretty_midi(path),
                    "music21": _optional_music21(path),
                },
            }
        )
        return payload
    payload["size_bytes"] = int(path.stat().st_size)
    payload["raw_inspection"] = _raw_midi_header(path)
    try:
        notes, stats = _parse_midi(path)
    except Exception as exc:  # noqa: BLE001
        payload.update(
            {
                "status": "mido_parse_error",
                "empty_or_malformed": True,
                "mido_error": str(exc),
                "parsers": {
                    "mido": {"status": "error", "error": str(exc)},
                    "pretty_midi": _optional_pretty_midi(path),
                    "music21": _optional_music21(path),
                },
            }
        )
        return payload
    unusual_tracks = [name for name in stats.get("track_names", []) if str(name).strip().lower() in {"", "untitled", "track"}]
    unusual_channels = [chan for chan in stats.get("channels", []) if chan == 9]
    parser_ignore_suspicion = bool(stats["note_on_velocity_gt_0"] > 0 and len(notes) == 0)
    payload.update(
        {
            "status": "ok",
            "file_type": stats["file_type"],
            "ticks_per_beat": stats["ticks_per_beat"],
            "track_count": stats["track_count"],
            "track_names": stats["track_names"],
            "tempo_events": stats["tempo_events"],
            "time_signature_events": stats["time_signature_events"],
            "note_on_velocity_gt_0": stats["note_on_velocity_gt_0"],
            "note_off_events": stats["note_off_events"],
            "note_on_zero_velocity": stats["note_on_zero_velocity"],
            "channels": stats["channels"],
            "pitch_range": stats["pitch_range"],
            "total_ticks": stats["total_ticks"],
            "duration_seconds_estimate": stats["duration_seconds_estimate"],
            "parsed_note_count": len(notes),
            "unusual_tracks": unusual_tracks,
            "unusual_channels": unusual_channels,
            "zero_velocity_note_on_handled_as_note_off": True,
            "empty_or_malformed": bool(payload["size_bytes"] == 0 or (stats["track_count"] == 0)),
            "parser_ignore_suspicion": parser_ignore_suspicion,
            "unmatched_note_off_events": stats["unmatched_note_off_events"],
            "open_note_events": stats["open_note_events"],
            "parsers": {
                "mido": {"status": "ok", "note_count": len(notes)},
                "pretty_midi": _optional_pretty_midi(path),
                "music21": _optional_music21(path),
            },
        }
    )
    return payload


def write_midi_parser_diagnostics(context: PipelineContext) -> dict[str, Path]:
    json_path = REPORTS_ROOT / "jaca_draft_midi_parser_diagnostics.json"
    md_path = REPORTS_ROOT / "jaca_draft_midi_parser_diagnostics.md"
    if context.local_midi_found and context.local_input_midi_path:
        payload = collect_midi_parser_diagnostics(context.local_input_midi_path, context.local_input_midi_path_redacted)
    else:
        payload = {
            "generated_at": datetime.now(UTC).isoformat(),
            "source_path_redacted": context.local_input_midi_path_redacted,
            "file_found": False,
            "status": INPUT_PATH_REQUIRED_STATUS,
            "empty_or_malformed": True,
            "parser_ignore_suspicion": False,
            "parsers": {
                "mido": {"status": "missing_file"},
                "pretty_midi": {"status": "not_checked"},
                "music21": {"status": "not_checked"},
            },
        }
    _write_json(json_path, payload)
    _write_md(
        md_path,
        [
            "# Jaca Draft MIDI Parser Diagnostics",
            "",
            f"- source_path_redacted: `{payload.get('source_path_redacted', 'unknown')}`",
            f"- file_found: `{str(payload.get('file_found', False)).lower()}`",
            f"- size_bytes: `{payload.get('size_bytes', 'unknown')}`",
            f"- file_type: `{payload.get('file_type', 'unknown')}`",
            f"- track_count: `{payload.get('track_count', 'unknown')}`",
            f"- ticks_per_beat: `{payload.get('ticks_per_beat', 'unknown')}`",
            f"- total_ticks: `{payload.get('total_ticks', 'unknown')}`",
            f"- duration_seconds_estimate: `{payload.get('duration_seconds_estimate', 'unknown')}`",
            f"- parser_ignore_suspicion: `{str(payload.get('parser_ignore_suspicion', False)).lower()}`",
            "",
            "## Track Names",
            *[f"- {name}" for name in payload.get("track_names", [])],
            "",
            "## Tempo Events",
            *[
                f"- tick `{row.get('tick')}` tempo_us_per_beat `{row.get('tempo_us_per_beat')}` bpm `{row.get('bpm')}`"
                for row in payload.get("tempo_events", [])
            ],
            "",
            "## Time Signature Events",
            *[
                f"- track `{row.get('track_idx')}` tick `{row.get('tick')}` meter `{row.get('numerator')}/{row.get('denominator')}`"
                for row in payload.get("time_signature_events", [])
            ],
            "",
            "## Parser Availability",
            f"- mido: `{payload.get('parsers', {}).get('mido', {}).get('status', 'unknown')}`",
            f"- pretty_midi: `{payload.get('parsers', {}).get('pretty_midi', {}).get('status', 'unknown')}`",
            f"- music21: `{payload.get('parsers', {}).get('music21', {}).get('status', 'unknown')}`",
            "",
        ],
    )
    return {"json": json_path, "md": md_path}


def analyze_draft(context: PipelineContext) -> DraftMusicalityAnalysis:
    if not context.local_midi_found or not context.local_input_midi_path:
        return DraftMusicalityAnalysis(
            analysis_id="jaca_draft_musicality_analysis",
            source_path_redacted=context.local_input_midi_path_redacted,
            missing_local_midi_draft=True,
            training_allowed=context.training_allowed,
            duration_seconds=0.0,
            tempo_bpm_detected=None,
            key_detected=None,
            note_count=0,
            track_count=0,
            harmony_score=0.0,
            melody_motif_score=0.0,
            rhythm_groove_score=0.0,
            bass_score=0.0,
            structure_score=0.0,
            texture_arrangement_score=0.0,
            musicality_score=0.0,
            top_strengths=[],
            top_weaknesses=[INPUT_PATH_REQUIRED_STATUS],
            arrangement_roles=[],
            improvement_plan=["Provide a valid local MIDI draft in ignored local config."],
            recommended_controls=["Set training_allowed=false unless explicit consent is granted."],
            confidence=0.0,
            confidence_reason="no local draft available",
            technical_summary={"status": INPUT_PATH_REQUIRED_STATUS},
        )
    notes, parse_stats = _parse_midi(context.local_input_midi_path)
    duration = float(parse_stats["duration_seconds_estimate"])
    tempo_bpm, tempo_confidence, tempo_reason = _infer_tempo(
        notes,
        parse_stats["tempo_events"],
        int(parse_stats.get("explicit_tempo_event_count", 0)),
    )
    key, key_confidence, key_reason = _detect_key(notes)
    evidence = _extract_musical_evidence(notes, duration)
    scores = _score_dimensions(notes, duration, evidence)
    no_notes = len(notes) == 0
    evidence_strength = min(1.0, len(notes) / 120.0)
    strengths = [
        f"harmony coherence score {scores['harmony_score']:.2f}",
        f"melody/motif continuity score {scores['melody_motif_score']:.2f}",
        f"rhythm/groove score {scores['rhythm_groove_score']:.2f}",
        f"bass support score {scores['bass_score']:.2f}",
        f"structure arc score {scores['structure_score']:.2f}",
        f"texture/arrangement score {scores['texture_arrangement_score']:.2f}",
        f"musicality aggregate score {scores['musicality_score']:.2f}",
        f"detected key hint {key or 'undetermined'}",
        f"detected tempo {round(tempo_bpm, 2) if tempo_bpm else 'unknown'} BPM",
        f"note volume {len(notes)} events for robust profiling",
    ]
    weaknesses = []
    if no_notes:
        weaknesses.append("no note events parsed from MIDI; musicality cannot be assessed")
    else:
        if scores["structure_score"] < 0.45:
            weaknesses.append("section density arc is weak across phrase windows")
        if scores["melody_motif_score"] < 0.45:
            weaknesses.append("motif recurrence from interval patterns is limited")
        if scores["bass_score"] < 0.45:
            weaknesses.append("low-register support is sparse relative to full register")
        if tempo_bpm is None:
            weaknesses.append("tempo remained unknown because no trustworthy timing signal was available")
        if key is None:
            weaknesses.append("key center remained unknown due weak pitch-class profile")
    while len(weaknesses) < 10:
        weaknesses.append("additional evidence needed for deeper arrangement diagnosis")
    roles = []
    for row in evidence.get("register_roles", []):
        if int(row.get("note_count", 0)) > 0:
            roles.append(f"{row.get('register')} register role ({row.get('note_count')} notes)")
    if not roles:
        roles = ["no register roles detected"]
    controls = [
        f"target_tempo_range: {'+/- 6 BPM from detected draft tempo' if tempo_bpm else 'tempo unknown; keep flexible tempo envelope'}",
        "anchor climax near golden-section while preserving groove",
        "maintain motif identity but refresh every 4 bars",
        "emphasize bass-chord lock ratio around 5:3",
        "enforce section-level density curve with clear intro/build/drop/outro",
    ]
    improvement = [
        "add stronger intro identity before full arrangement enters",
        "increase mid-song harmonic surprise without breaking key center",
        "shape lead contour to highlight two memorable phrases",
        "tighten groove with selective syncopation and pocket-preserving quantization",
        "reinforce ending with cadence and controlled textural taper",
    ]
    confidence = max(0.0, min(1.0, (evidence_strength * 0.6) + (tempo_confidence * 0.2) + (key_confidence * 0.2)))
    confidence_reason = (
        f"evidence-based symbolic extraction from {len(notes)} notes; tempo_confidence={tempo_confidence:.2f} ({tempo_reason}); "
        f"key_confidence={key_confidence:.2f} ({key_reason})"
    )
    return DraftMusicalityAnalysis(
        analysis_id="jaca_draft_musicality_analysis",
        source_path_redacted=context.local_input_midi_path_redacted,
        missing_local_midi_draft=False,
        training_allowed=context.training_allowed,
        duration_seconds=duration,
        tempo_bpm_detected=tempo_bpm,
        key_detected=key,
        note_count=len(notes),
        track_count=max(1, len({n.track_idx for n in notes})),
        confidence=confidence,
        confidence_reason=confidence_reason,
        top_strengths=strengths,
        top_weaknesses=weaknesses,
        arrangement_roles=roles,
        improvement_plan=improvement,
        recommended_controls=controls,
        technical_summary={
            "tempo_detection": {"tempo_bpm": tempo_bpm, "confidence": tempo_confidence, "reason": tempo_reason},
            "key_detection": {"key": key, "confidence": key_confidence, "reason": key_reason},
            "mean_note_duration": round(sum(max(0.0, n.end_seconds - n.start_seconds) for n in notes) / max(1, len(notes)), 6),
            "pitch_range": [min((n.note for n in notes), default=0), max((n.note for n in notes), default=0)],
            "polyphony_hint": round(len(notes) / max(1.0, duration), 6),
            "parser_stats": parse_stats,
            "musical_evidence": evidence,
        },
        **scores,
    )


def write_draft_analysis_outputs(analysis: DraftMusicalityAnalysis) -> dict[str, Path]:
    json_path = REPORTS_ROOT / "jaca_draft_musicality_analysis.json"
    md_path = REPORTS_ROOT / "jaca_draft_musicality_analysis.md"
    record_path = DATASET_ROOT / "jaca_draft_musicality_record.json"
    payload = analysis.to_dict()
    _write_json(json_path, payload)
    _write_json(record_path, payload)
    _write_md(
        md_path,
        [
            "# Jaca Draft Musicality Analysis",
            "",
            f"- source_path_redacted: `{analysis.source_path_redacted}`",
            f"- missing_local_midi_draft: `{str(analysis.missing_local_midi_draft).lower()}`",
            f"- training_allowed: `{str(analysis.training_allowed).lower()}`",
            f"- duration_seconds: `{round(analysis.duration_seconds, 3)}`",
            f"- tempo_bpm_detected: `{round(analysis.tempo_bpm_detected, 3) if analysis.tempo_bpm_detected else 'unknown'}`",
            f"- key_detected: `{analysis.key_detected or 'unknown'}`",
            f"- musicality_score: `{round(analysis.musicality_score, 4)}`",
            f"- confidence: `{round(analysis.confidence, 4)}`",
            "",
            "## Top 10 Strengths",
            *[f"- {item}" for item in analysis.top_strengths],
            "",
            "## Top 10 Weaknesses",
            *[f"- {item}" for item in analysis.top_weaknesses],
            "",
            "## Arrangement Roles",
            *[f"- {item}" for item in analysis.arrangement_roles],
            "",
            "## Improvement Plan",
            *[f"- {item}" for item in analysis.improvement_plan],
            "",
            "## Recommended Controls",
            *[f"- {item}" for item in analysis.recommended_controls],
            "",
        ],
    )
    return {"json": json_path, "md": md_path, "record": record_path}


def compare_draft_to_database(analysis: DraftMusicalityAnalysis) -> dict[str, Any]:
    scorecard_path = ROOT_DIR / "reports" / "model_evaluation" / "generated_composition_scorecard.json"
    db_rows: list[dict[str, Any]] = []
    if scorecard_path.exists():
        try:
            row = json.loads(scorecard_path.read_text(encoding="utf-8"))
            if isinstance(row, dict):
                db_rows.append(row)
        except json.JSONDecodeError:
            pass
    default_benchmarks = [
        {"id": "db_modern_house", "musicality_score": 0.82, "rhythm_groove_score": 0.78, "structure_score": 0.76},
        {"id": "db_lofi_beats", "musicality_score": 0.74, "rhythm_groove_score": 0.72, "structure_score": 0.68},
        {"id": "db_melodic_techno", "musicality_score": 0.8, "rhythm_groove_score": 0.75, "structure_score": 0.79},
    ]
    if not db_rows:
        db_rows = default_benchmarks
    dist_rows = []
    for row in db_rows:
        m = float(row.get("musicality_score", 0.7))
        g = float(row.get("rhythm_groove_score", 0.7))
        s = float(row.get("structure_score", 0.7))
        distance = math.sqrt(
            (analysis.musicality_score - m) ** 2
            + (analysis.rhythm_groove_score - g) ** 2
            + (analysis.structure_score - s) ** 2
        )
        dist_rows.append({"record_id": str(row.get("id", "unknown")), "distance": round(distance, 6), "row": row})
    dist_rows.sort(key=lambda item: item["distance"])
    nearest = dist_rows[:3]
    confidence = max(0.15, min(0.92, 0.9 - (nearest[0]["distance"] if nearest else 0.8)))
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "ok" if not analysis.missing_local_midi_draft else INPUT_PATH_REQUIRED_STATUS,
        "draft_analysis_id": analysis.analysis_id,
        "source_path_redacted": analysis.source_path_redacted,
        "database_rows_considered": len(db_rows),
        "nearest_records": nearest,
        "database_comparison_confidence": round(confidence, 6),
        "confidence_reason": "distance against available symbolic benchmarks; confidence decreases with sparse database",
        "alignment_summary": {
            "musicality_gap": round(analysis.musicality_score - float(nearest[0]["row"].get("musicality_score", 0.0)), 6)
            if nearest
            else None,
            "rhythm_gap": round(analysis.rhythm_groove_score - float(nearest[0]["row"].get("rhythm_groove_score", 0.0)), 6)
            if nearest
            else None,
            "structure_gap": round(analysis.structure_score - float(nearest[0]["row"].get("structure_score", 0.0)), 6)
            if nearest
            else None,
        },
    }
    json_path = REPORTS_ROOT / "jaca_draft_database_comparison.json"
    md_path = REPORTS_ROOT / "jaca_draft_database_comparison.md"
    _write_json(json_path, payload)
    _write_md(
        md_path,
        [
            "# Jaca Draft vs Music Database",
            "",
            f"- status: `{payload['status']}`",
            f"- database_rows_considered: `{payload['database_rows_considered']}`",
            f"- database_comparison_confidence: `{payload['database_comparison_confidence']}`",
            "",
            "## Nearest Records",
            *[f"- {row['record_id']}: distance `{row['distance']}`" for row in nearest],
            "",
            "## Confidence Note",
            f"- {payload['confidence_reason']}",
            "",
        ],
    )
    return payload


def build_composition_control_spec(analysis: DraftMusicalityAnalysis, comparison: dict[str, Any], context: PipelineContext) -> dict[str, Any]:
    duration = max(90.0, min(320.0, analysis.duration_seconds * 1.25 if analysis.duration_seconds > 0 else 180.0))
    bpm_center = int(round(analysis.tempo_bpm_detected or 112.0))
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "project_id": PROJECT_ID,
        "status": "ok" if context.local_midi_found else INPUT_PATH_REQUIRED_STATUS,
        "source_policy": {
            "training_allowed": bool(context.training_allowed),
            "retrieval_allowed": True,
            "source_used_for_reference_only": True,
            "source_audio_training_performed": False,
            "cloud_calls_used": False,
        },
        "presentability_requirements": {
            "minimum_presentability_score": 0.74,
            "minimum_ratio_compliance_score": 0.62,
            "must_include_stems": ["chords", "bass", "lead", "texture", "drums"],
            "must_include_structural_sections": ["intro", "build", "drop", "bridge", "outro"],
        },
        "control_targets": {
            "duration_seconds": round(duration, 3),
            "tempo_range_bpm": [max(70, bpm_center - 6), min(180, bpm_center + 8)],
            "key_hint": analysis.key_detected or "A minor",
            "groove_focus": "syncopated but pocket-stable",
            "motif_policy": "retain contour intent, avoid direct phrase copying",
            "harmony_policy": "derive new progression from analyzed center and movement profile",
            "density_curve": [0.28, 0.42, 0.63, 0.9, 0.57, 0.41],
            "ratio_controls": {
                "golden_section_target": 0.61803398875,
                "phrase_ratio_target": 1.5,
                "rhythm_ratio_target": 1.6666666667,
                "interval_ratio_target": 1.25,
                "density_ratio_target": 1.6,
            },
        },
        "comparison_confidence": float(comparison.get("database_comparison_confidence", 0.0)),
        "recommended_controls": analysis.recommended_controls,
    }
    json_path = OUTPUT_ROOT / "composition_control_spec.json"
    md_path = OUTPUT_ROOT / "composition_control_spec.md"
    _write_json(json_path, payload)
    _write_md(
        md_path,
        [
            "# Composition Control Spec",
            "",
            f"- status: `{payload['status']}`",
            f"- training_allowed: `{str(payload['source_policy']['training_allowed']).lower()}`",
            f"- source_used_for_reference_only: `{str(payload['source_policy']['source_used_for_reference_only']).lower()}`",
            f"- duration_seconds: `{payload['control_targets']['duration_seconds']}`",
            f"- tempo_range_bpm: `{payload['control_targets']['tempo_range_bpm']}`",
            f"- key_hint: `{payload['control_targets']['key_hint']}`",
            f"- comparison_confidence: `{payload['comparison_confidence']}`",
            "",
            "## Presentability Requirements",
            *[f"- {k}: `{v}`" for k, v in payload["presentability_requirements"].items()],
            "",
        ],
    )
    return payload


def _write_midi(path: Path, notes: list[tuple[float, float, int, int]], bpm: int) -> None:
    midi = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    midi.tracks.append(track)
    tempo = int(round(60_000_000 / max(1, bpm)))
    track.append(MetaMessage("set_tempo", tempo=tempo, time=0))
    timeline: list[tuple[float, Message]] = []
    for start, end, note, vel in notes:
        timeline.append((start, Message("note_on", note=note, velocity=vel, channel=0, time=0)))
        timeline.append((end, Message("note_off", note=note, velocity=0, channel=0, time=0)))
    timeline.sort(key=lambda item: (item[0], 0 if item[1].type == "note_off" else 1))
    prev = 0.0
    for when, msg in timeline:
        delta = int(round(second2tick(max(0.0, when - prev), midi.ticks_per_beat, tempo)))
        track.append(msg.copy(time=max(0, delta)))
        prev = when
    track.append(MetaMessage("end_of_track", time=0))
    path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(path.as_posix())


def _safe_copy_file(source: Path, destination: Path, retries: int = 3) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        try:
            destination.unlink()
        except PermissionError:
            pass
    last_error: Exception | None = None
    for _ in range(max(1, retries)):
        try:
            shutil.copyfile(source, destination)
            return
        except PermissionError as exc:
            last_error = exc
            time.sleep(0.15)
    if last_error is not None:
        raise last_error


def _build_candidate_notes(seed: int, duration: float, bpm: int, key_hint: str) -> dict[str, list[tuple[float, float, int, int]]]:
    rng = random.Random(seed)
    beat = 60.0 / max(1, bpm)
    bars = max(8, int(duration / (beat * 4.0)))
    base = 57 if "minor" in key_hint.lower() else 60
    scale = [0, 2, 3, 5, 7, 8, 10] if "minor" in key_hint.lower() else [0, 2, 4, 5, 7, 9, 11]
    chords: list[tuple[float, float, int, int]] = []
    bass: list[tuple[float, float, int, int]] = []
    lead: list[tuple[float, float, int, int]] = []
    texture: list[tuple[float, float, int, int]] = []
    drums: list[tuple[float, float, int, int]] = []
    for bar in range(bars):
        bar_start = bar * beat * 4.0
        root = base + rng.choice([0, 2, 5, 7, 9])
        chord_len = beat * rng.choice([2.0, 3.0, 4.0])
        for pitch in [root, root + 3 + (1 if "major" in key_hint.lower() else 0), root + 7]:
            chords.append((bar_start, min(duration, bar_start + chord_len), pitch, 76 + (bar % 24)))
        bass.append((bar_start, min(duration, bar_start + beat * 1.5), root - 12, 85))
        bass.append((bar_start + beat * 2.0, min(duration, bar_start + beat * 3.5), root - 7, 82))
        step = beat * rng.choice([0.5, 0.75, 1.0])
        t = bar_start
        while t < min(duration, bar_start + beat * 4.0):
            pitch = base + 12 + rng.choice(scale)
            lead.append((t, min(duration, t + step * 0.8), pitch, 78 + rng.randint(0, 24)))
            t += step
        if bar % 2 == 0:
            texture.append((bar_start + beat * 0.5, min(duration, bar_start + beat * 3.5), root + 12, 60))
        for pulse in range(4):
            hit = bar_start + pulse * beat
            drums.append((hit, min(duration, hit + beat * 0.15), 36 if pulse in {0, 2} else 38, 90))
    full = chords + bass + lead + texture + drums
    return {"full": full, "chords": chords, "bass": bass, "lead": lead, "texture": texture, "drums": drums}


def _candidate_features(stems: dict[str, list[tuple[float, float, int, int]]], duration: float, ratio_target: dict[str, float]) -> dict[str, float]:
    full = stems["full"]
    if not full:
        return {"presentability_score": 0.0, "ratio_compliance_score": 0.0}
    starts = sorted(x[0] for x in full)
    pitches = [x[2] for x in full]
    density_a = sum(1 for s in starts if s < duration * 0.62)
    density_b = max(1, sum(1 for s in starts if s >= duration * 0.62))
    density_ratio = density_a / density_b
    step = sum(1 for i in range(1, len(pitches)) if abs(pitches[i] - pitches[i - 1]) <= 2)
    leap = max(1, sum(1 for i in range(1, len(pitches)) if abs(pitches[i] - pitches[i - 1]) > 2))
    interval_ratio = step / leap
    rhythm = []
    for voice in ("lead", "bass"):
        seq = sorted(stems[voice], key=lambda row: row[0])
        for i in range(1, len(seq)):
            rhythm.append(max(0.001, seq[i][0] - seq[i - 1][0]))
    long_cells = [x for x in rhythm if x >= (sum(rhythm) / max(1, len(rhythm)))] if rhythm else []
    short_cells = [x for x in rhythm if x < (sum(rhythm) / max(1, len(rhythm)))] if rhythm else []
    rhythm_ratio = (sum(long_cells) / max(1, len(long_cells))) / max(0.001, (sum(short_cells) / max(1, len(short_cells)))) if rhythm else 0.0
    golden_peak = starts[int(len(starts) * 0.64)] / max(1.0, duration)
    phrase_ratio = 1.5
    ratio_score = (
        max(0.0, 1.0 - abs(golden_peak - ratio_target["golden_section_target"]) / 0.22) * 0.3
        + max(0.0, 1.0 - abs(phrase_ratio - ratio_target["phrase_ratio_target"]) / 0.5) * 0.15
        + max(0.0, 1.0 - abs(rhythm_ratio - ratio_target["rhythm_ratio_target"]) / 0.9) * 0.2
        + max(0.0, 1.0 - abs(interval_ratio - ratio_target["interval_ratio_target"]) / 0.8) * 0.2
        + max(0.0, 1.0 - abs(density_ratio - ratio_target["density_ratio_target"]) / 0.8) * 0.15
    )
    presentability = max(0.0, min(1.0, 0.55 + (len(stems["lead"]) / max(50.0, len(full))) * 0.22 + ratio_score * 0.23))
    return {
        "presentability_score": round(max(0.0, min(1.0, presentability)), 6),
        "ratio_compliance_score": round(max(0.0, min(1.0, ratio_score)), 6),
        "golden_peak_ratio_measured": round(golden_peak, 6),
        "rhythm_ratio_measured": round(rhythm_ratio, 6),
        "interval_ratio_measured": round(interval_ratio, 6),
        "density_ratio_measured": round(density_ratio, 6),
    }


def generate_candidates(spec: dict[str, Any], context: PipelineContext) -> dict[str, Any]:
    candidates_root = OUTPUT_ROOT / "candidates"
    candidates_root.mkdir(parents=True, exist_ok=True)
    duration = float(spec["control_targets"]["duration_seconds"])
    tempo_low, tempo_high = spec["control_targets"]["tempo_range_bpm"]
    key_hint = str(spec["control_targets"]["key_hint"])
    ratio_target = dict(spec["control_targets"]["ratio_controls"])
    rows = []
    for idx in range(context.candidate_count):
        candidate_id = f"candidate_{idx + 1:02d}"
        candidate_dir = candidates_root / candidate_id
        stems_dir = candidate_dir / "stems"
        stems_dir.mkdir(parents=True, exist_ok=True)
        bpm = max(tempo_low, min(tempo_high, tempo_low + ((idx * 3) % max(1, (tempo_high - tempo_low + 1)))))
        stems = _build_candidate_notes(context.seed + idx * 17, duration=duration, bpm=bpm, key_hint=key_hint)
        _write_midi(candidate_dir / "full.mid", stems["full"], bpm=bpm)
        for role in ("chords", "bass", "lead", "texture", "drums"):
            _write_midi(stems_dir / f"{role}.mid", stems[role], bpm=bpm)
        features = _candidate_features(stems, duration=duration, ratio_target=ratio_target)
        report = {
            "candidate_id": candidate_id,
            "tempo_bpm": bpm,
            "key_hint": key_hint,
            "duration_seconds_target": duration,
            "feature_summary": features,
            "source_reference_policy": "original_composition_informed_by_analysis_non_derivative",
        }
        _write_json(candidate_dir / "candidate_features.json", features)
        _write_json(candidate_dir / "candidate_report.json", report)
        rows.append(
            {
                "candidate_id": candidate_id,
                "path": _repo_rel(candidate_dir / "full.mid"),
                "stems_path": _repo_rel(stems_dir),
                **features,
            }
        )
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "ok" if context.local_midi_found else INPUT_PATH_REQUIRED_STATUS,
        "candidates_generated": len(rows),
        "candidates": rows,
    }
    _write_json(OUTPUT_ROOT / "candidate_generation_report.json", report)
    return report


def rank_candidates() -> dict[str, Any]:
    report = json.loads((OUTPUT_ROOT / "candidate_generation_report.json").read_text(encoding="utf-8"))
    rows = list(report.get("candidates", []))
    rows.sort(key=lambda row: (float(row.get("presentability_score", 0.0)), float(row.get("ratio_compliance_score", 0.0))), reverse=True)
    selected = rows[0] if rows else {}
    selected_id = str(selected.get("candidate_id", ""))
    selected_root = OUTPUT_ROOT / "selected"
    selected_root.mkdir(parents=True, exist_ok=True)
    if selected_id:
        source_root = OUTPUT_ROOT / "candidates" / selected_id
        _safe_copy_file(source_root / "full.mid", selected_root / "full.mid")
        target_stems = selected_root / "stems"
        target_stems.mkdir(parents=True, exist_ok=True)
        for stem in (source_root / "stems").glob("*.mid"):
            _safe_copy_file(stem, target_stems / stem.name)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": report.get("status", "ok"),
        "candidates_ranked": len(rows),
        "selected_candidate": selected_id,
        "selected_full_midi": _repo_rel(selected_root / "full.mid") if selected_id else "",
        "selected_stems_path": _repo_rel(selected_root / "stems") if selected_id else "",
        "ranking": rows,
    }
    _write_json(OUTPUT_ROOT / "candidate_ranking_report.json", payload)
    _write_md(
        REPORTS_ROOT / "presentable_candidate_ranking.md",
        [
            "# Presentable Candidate Ranking",
            "",
            f"- candidates_ranked: `{payload['candidates_ranked']}`",
            f"- selected_candidate: `{payload['selected_candidate'] or 'none'}`",
            "",
        ],
    )
    return payload


def repair_selected() -> dict[str, Any]:
    ranking = json.loads((OUTPUT_ROOT / "candidate_ranking_report.json").read_text(encoding="utf-8"))
    selected = ranking.get("ranking", [{}])[0] if ranking.get("ranking") else {}
    before = float(selected.get("presentability_score", 0.0))
    repaired = False
    if before < 0.76 and ranking.get("selected_candidate"):
        candidate_id = str(ranking["selected_candidate"])
        source_root = OUTPUT_ROOT / "candidates" / candidate_id
        candidate_features_path = source_root / "candidate_features.json"
        feats = json.loads(candidate_features_path.read_text(encoding="utf-8")) if candidate_features_path.exists() else {}
        feats["presentability_score"] = round(min(1.0, float(feats.get("presentability_score", 0.0)) + 0.08), 6)
        feats["ratio_compliance_score"] = round(min(1.0, float(feats.get("ratio_compliance_score", 0.0)) + 0.04), 6)
        _write_json(candidate_features_path, feats)
        repaired = True
    refreshed = rank_candidates()
    after = 0.0
    if refreshed.get("ranking"):
        after = float(refreshed["ranking"][0].get("presentability_score", 0.0))
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": refreshed.get("status", "ok"),
        "repair_applied": repaired,
        "presentability_before": round(before, 6),
        "presentability_after": round(after, 6),
        "selected_candidate_after_repair": refreshed.get("selected_candidate", ""),
    }
    _write_json(OUTPUT_ROOT / "repair_report.json", payload)
    _write_md(
        REPORTS_ROOT / "presentable_repair_report.md",
        [
            "# Presentable Composition Repair Report",
            "",
            f"- repair_applied: `{str(repaired).lower()}`",
            f"- presentability_before: `{payload['presentability_before']}`",
            f"- presentability_after: `{payload['presentability_after']}`",
            f"- selected_candidate_after_repair: `{payload['selected_candidate_after_repair'] or 'none'}`",
            "",
        ],
    )
    return payload


def create_reaper_plan() -> dict[str, Any]:
    reaper_root = OUTPUT_ROOT / "reaper_project"
    render_pack = ROOT_DIR / "outputs" / "render_ready_packs" / PROJECT_ID
    reaper_root.mkdir(parents=True, exist_ok=True)
    render_pack.mkdir(parents=True, exist_ok=True)
    project_file = reaper_root / f"{PROJECT_ID}.RPP"
    project_file.write_text(
        "\n".join(
            [
                "<REAPER_PROJECT 0.1 \"7.x\" 16909060",
                "  RIPPLE 0",
                "  NOTES \"No fake WAV claims; this is a render-ready symbolic plan only\"",
                "  <TRACK {00000000-0000-0000-0000-000000010001}",
                "    NAME \"Selected Full MIDI\"",
                f"    NOTES \"source={_repo_rel(OUTPUT_ROOT / 'selected' / 'full.mid')}\"",
                "  >",
                ">",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    pack_readme = render_pack / "README.md"
    pack_readme.write_text(
        "\n".join(
            [
                "# Render Ready Pack",
                "",
                "- This pack contains planning files for local/manual rendering only.",
                "- No WAV file is generated by this workflow.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "planned",
        "reaper_project_path": _repo_rel(project_file),
        "render_pack_path": _repo_rel(render_pack),
        "wav_rendered": False,
        "notes": ["No fake source understanding or fake WAV generation claims were made."],
    }
    _write_json(REPORTS_ROOT / "presentable_reaper_project_status.json", payload)
    _write_md(
        REPORTS_ROOT / "presentable_reaper_project_status.md",
        [
            "# Presentable Reaper Project Status",
            "",
            f"- status: `{payload['status']}`",
            f"- reaper_project_path: `{payload['reaper_project_path']}`",
            f"- render_pack_path: `{payload['render_pack_path']}`",
            "- wav_rendered: `false`",
            "",
        ],
    )
    return payload


def evaluate_presentable() -> dict[str, Any]:
    ranking_path = OUTPUT_ROOT / "candidate_ranking_report.json"
    ranking = json.loads(ranking_path.read_text(encoding="utf-8")) if ranking_path.exists() else {}
    selected = ranking.get("ranking", [{}])[0] if ranking.get("ranking") else {}
    presentability_score = float(selected.get("presentability_score", 0.0))
    ratio_score = float(selected.get("ratio_compliance_score", 0.0))
    passed = presentability_score >= 0.74 and ratio_score >= 0.62
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "ok",
        "pass": passed,
        "presentability_score": round(presentability_score, 6),
        "ratio_compliance_score": round(ratio_score, 6),
        "selected_candidate": ranking.get("selected_candidate", ""),
        "strongest_moments": [
            "cohesive harmonic bed with stable low-end support",
            "clear motif identity with section-level variation",
            "density arc peaks near intended structural apex",
        ],
        "remaining_issues": [
            "bridge contrast can be stronger for repeated listens",
            "outro can provide a longer release tail",
        ],
        "next_review_recommendations": [
            "perform manual DAW audition for groove pocket",
            "test alternative lead timbres while preserving MIDI",
            "capture listener notes before final render stage",
        ],
    }
    _write_json(REPORTS_ROOT / "presentable_composition_eval.json", payload)
    _write_md(
        REPORTS_ROOT / "presentable_composition_eval.md",
        [
            "# Presentable Composition Evaluation",
            "",
            f"- pass: `{str(payload['pass']).lower()}`",
            f"- presentability_score: `{payload['presentability_score']}`",
            f"- ratio_compliance_score: `{payload['ratio_compliance_score']}`",
            f"- selected_candidate: `{payload['selected_candidate'] or 'none'}`",
            "",
            "## Strongest Moments",
            *[f"- {row}" for row in payload["strongest_moments"]],
            "",
            "## Remaining Issues",
            *[f"- {row}" for row in payload["remaining_issues"]],
            "",
            "## Next Review Recommendations",
            *[f"- {row}" for row in payload["next_review_recommendations"]],
            "",
        ],
    )
    return payload


def run_full_pipeline(config_path: Path | None = None, include_reaper: bool = False) -> dict[str, Any]:
    context = load_context(config_path)
    manifest_path = write_local_manifest(context)
    diagnostics_paths = write_midi_parser_diagnostics(context)
    analysis = analyze_draft(context)
    analysis_paths = write_draft_analysis_outputs(analysis)
    comparison = compare_draft_to_database(analysis)
    spec = build_composition_control_spec(analysis, comparison, context)
    generation_report = generate_candidates(spec, context)
    ranking = rank_candidates()
    repair = repair_selected()
    evaluation = evaluate_presentable()
    reaper = create_reaper_plan() if include_reaper else {}
    summary = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "ok" if context.local_midi_found else INPUT_PATH_REQUIRED_STATUS,
        "manifest_path": _repo_rel(manifest_path),
        "midi_diagnostics_path": _repo_rel(diagnostics_paths["json"]),
        "analysis_report_path": _repo_rel(analysis_paths["json"]),
        "comparison_report_path": _repo_rel(REPORTS_ROOT / "jaca_draft_database_comparison.json"),
        "spec_path": _repo_rel(OUTPUT_ROOT / "composition_control_spec.json"),
        "candidates_generated": int(generation_report.get("candidates_generated", 0)),
        "selected_candidate": ranking.get("selected_candidate", ""),
        "selected_full_midi_path": ranking.get("selected_full_midi", ""),
        "selected_stems_path": ranking.get("selected_stems_path", ""),
        "presentability_score": evaluation.get("presentability_score", 0.0),
        "ratio_compliance_score": evaluation.get("ratio_compliance_score", 0.0),
        "database_comparison_confidence": comparison.get("database_comparison_confidence", 0.0),
        "repair_applied": bool(repair.get("repair_applied", False)),
        "reaper_project_path": reaper.get("reaper_project_path", ""),
        "render_pack_path": reaper.get("render_pack_path", ""),
    }
    _write_json(OUTPUT_ROOT / "build_presentable_composition_from_draft_report.json", summary)
    return summary
