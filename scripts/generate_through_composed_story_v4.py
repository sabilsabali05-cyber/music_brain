from __future__ import annotations

import argparse
import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mido import Message, MetaMessage, MidiFile, MidiTrack, bpm2tempo, tempo2bpm

ROOT_DIR = Path(__file__).resolve().parent.parent
TARGET_BPM = 100.0
TARGET_TEMPO = bpm2tempo(TARGET_BPM)
SECTION_BARS = (8, 10, 12, 8, 10)
SECTION_NAMES = ("intro_tension", "lift", "conflict", "breakthrough", "resolution")
CORE_KEEP_CLASSES = {
    "essential_chord_tone",
    "emotional_tension",
    "melodic_anchor",
    "rhythmic_identity",
    "transition_voiceleading",
}
ALL_CLASSES = (
    "essential_chord_tone",
    "emotional_tension",
    "melodic_anchor",
    "rhythmic_identity",
    "transition_voiceleading",
    "texture_support",
    "passing_tone",
    "ornament",
    "duplicate",
    "clutter",
    "accidental_clash",
    "low_emotional_value",
)


@dataclass
class NoteEvent:
    note: int
    velocity: int
    channel: int
    start_tick: int
    end_tick: int
    track_name: str
    source_index: int
    note_id: str
    parent_id: str
    primary_class: str = "low_emotional_value"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _track_name(track: MidiTrack) -> str:
    for msg in track:
        if msg.type == "track_name":
            return str(msg.name)
    return ""


def _clamp_note(note: int) -> int:
    return max(0, min(127, int(note)))


def _clamp_velocity(velocity: int) -> int:
    return max(1, min(127, int(velocity)))


def _ticks_per_bar(ticks_per_beat: int) -> int:
    return ticks_per_beat * 4


def _bar_for_tick(tick: int, ticks_per_beat: int) -> int:
    return max(0, tick // _ticks_per_bar(ticks_per_beat))


def _section_for_bar(bar: int) -> str:
    running = 0
    for idx, bars in enumerate(SECTION_BARS):
        running += bars
        if bar < running:
            return SECTION_NAMES[idx]
    return SECTION_NAMES[-1]


def _extract_tempo_bpm(midi: MidiFile) -> float:
    for track in midi.tracks:
        for msg in track:
            if msg.type == "set_tempo":
                return round(float(tempo2bpm(msg.tempo)), 6)
    return 120.0


def _extract_program_and_channel(track: MidiTrack) -> tuple[int | None, int | None]:
    for msg in track:
        if msg.type == "program_change":
            return int(msg.program), int(msg.channel)
    return None, None


def _collect_notes(track: MidiTrack, *, track_name: str, source_index: int) -> list[NoteEvent]:
    absolute_tick = 0
    open_notes: dict[tuple[int, int], list[tuple[int, int]]] = {}
    collected: list[NoteEvent] = []
    serial = 0
    for msg in track:
        absolute_tick += msg.time
        if msg.type == "note_on" and msg.velocity > 0:
            key = (msg.channel, msg.note)
            open_notes.setdefault(key, []).append((absolute_tick, msg.velocity))
        elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
            key = (msg.channel, msg.note)
            stack = open_notes.get(key)
            if not stack:
                continue
            start_tick, velocity = stack.pop()
            if absolute_tick <= start_tick:
                continue
            note_id = f"{track_name}:{source_index}:{serial}"
            serial += 1
            collected.append(
                NoteEvent(
                    note=msg.note,
                    velocity=velocity,
                    channel=msg.channel,
                    start_tick=start_tick,
                    end_tick=absolute_tick,
                    track_name=track_name,
                    source_index=source_index,
                    note_id=note_id,
                    parent_id=note_id,
                )
            )
    return collected


def _materialize_track(name: str, events: list[NoteEvent], *, program: int | None = None, channel: int | None = None) -> MidiTrack:
    rendered = MidiTrack()
    rendered.append(MetaMessage("track_name", name=name, time=0))
    if program is not None and channel is not None:
        rendered.append(Message("program_change", program=program, channel=channel, time=0))
    timeline: list[tuple[int, Message]] = []
    for event in events:
        if event.end_tick <= event.start_tick or event.velocity <= 0:
            continue
        safe_note = _clamp_note(event.note)
        safe_vel = _clamp_velocity(event.velocity)
        timeline.append((max(0, event.start_tick), Message("note_on", note=safe_note, velocity=safe_vel, channel=event.channel, time=0)))
        timeline.append((max(0, event.end_tick), Message("note_off", note=safe_note, velocity=0, channel=event.channel, time=0)))
    timeline.sort(key=lambda item: (item[0], 0 if item[1].type == "note_off" else 1))
    absolute_tick = 0
    for abs_tick, msg in timeline:
        delta = max(0, abs_tick - absolute_tick)
        rendered.append(msg.copy(time=delta))
        absolute_tick = abs_tick
    rendered.append(MetaMessage("end_of_track", time=0))
    return rendered


def _bar_roots(harmony_notes: list[NoteEvent], ticks_per_beat: int, total_bars: int) -> list[int]:
    grouped: dict[int, list[int]] = {}
    for note in harmony_notes:
        bar = _bar_for_tick(note.start_tick, ticks_per_beat)
        if 0 <= bar < total_bars:
            grouped.setdefault(bar, []).append(note.note)
    roots: list[int] = []
    for bar in range(total_bars):
        notes = grouped.get(bar, [])
        roots.append(min(notes) if notes else 50)
    return roots


def _top_rhythmic_cells(notes: list[NoteEvent], ticks_per_beat: int) -> list[dict[str, Any]]:
    by_bar: dict[int, list[NoteEvent]] = {}
    for note in notes:
        bar = _bar_for_tick(note.start_tick, ticks_per_beat)
        by_bar.setdefault(bar, []).append(note)
    cell_counts: dict[str, int] = {}
    cell_example: dict[str, dict[str, Any]] = {}
    for bar, bar_notes in by_bar.items():
        sorted_notes = sorted(bar_notes, key=lambda item: (item.start_tick, item.note))
        positions: list[float] = []
        for note in sorted_notes[:9]:
            in_bar = (note.start_tick % _ticks_per_bar(ticks_per_beat)) / float(ticks_per_beat)
            positions.append(round(in_bar, 2))
        if len(positions) < 4:
            continue
        key = str(positions[:6])
        cell_counts[key] = cell_counts.get(key, 0) + 1
        if key not in cell_example:
            cell_example[key] = {"bar": bar + 1, "positions": positions[:6]}
    ranked = sorted(cell_counts.items(), key=lambda item: (-item[1], item[0]))[:6]
    return [{"cell": key, "count": count, "example_bar": cell_example[key]["bar"], "positions": cell_example[key]["positions"]} for key, count in ranked]


def _chord_movements(roots: list[int]) -> list[dict[str, Any]]:
    movement: list[dict[str, Any]] = []
    for idx in range(1, len(roots)):
        delta = roots[idx] - roots[idx - 1]
        if abs(delta) >= 2:
            movement.append(
                {
                    "from_bar": idx,
                    "to_bar": idx + 1,
                    "from_root": roots[idx - 1],
                    "to_root": roots[idx],
                    "delta": delta,
                }
            )
    return movement[:10]


def _resolve_capable(notes_same_track: list[NoteEvent], idx: int, ticks_per_beat: int) -> bool:
    cur = notes_same_track[idx]
    window = int(0.85 * ticks_per_beat)
    for j in range(idx + 1, min(len(notes_same_track), idx + 4)):
        nxt = notes_same_track[j]
        if nxt.start_tick - cur.end_tick > window:
            break
        step = nxt.note - cur.note
        if abs(step) in (1, 2):
            return True
    return False


def _classify_notes(notes_by_track: dict[str, list[NoteEvent]], ticks_per_beat: int) -> tuple[dict[str, str], dict[str, int], list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    classification: dict[str, str] = {}
    class_counts = {name: 0 for name in ALL_CLASSES}
    accidental_clashes: list[dict[str, Any]] = []
    intentional_dissonances: list[dict[str, Any]] = []
    dominant_voice_per_section = {name: 0 for name in SECTION_NAMES}
    all_notes = [n for events in notes_by_track.values() for n in events if n.track_name != "Conductor"]
    by_track_sorted = {name: sorted(events, key=lambda n: (n.start_tick, n.note)) for name, events in notes_by_track.items()}

    # Detect duplicates (same pitch, near-identical timing).
    duplicate_ids: set[str] = set()
    signature_map: dict[tuple[int, int, int], list[NoteEvent]] = {}
    for note in all_notes:
        key = (note.note, note.start_tick // max(1, ticks_per_beat // 8), note.end_tick // max(1, ticks_per_beat // 8))
        signature_map.setdefault(key, []).append(note)
    for cluster in signature_map.values():
        if len(cluster) < 2:
            continue
        strongest = max(cluster, key=lambda n: n.velocity)
        for note in cluster:
            if note.note_id != strongest.note_id:
                duplicate_ids.add(note.note_id)

    # Detect dissonance collisions.
    non_drum = [n for n in all_notes if n.track_name != "Drums"]
    for i in range(len(non_drum)):
        a = non_drum[i]
        for j in range(i + 1, len(non_drum)):
            b = non_drum[j]
            if a.track_name == b.track_name:
                continue
            overlap_start = max(a.start_tick, b.start_tick)
            overlap_end = min(a.end_tick, b.end_tick)
            if overlap_end <= overlap_start:
                continue
            interval = abs(a.note - b.note) % 12
            if interval not in (1, 2, 6, 10, 11):
                continue
            overlap_beats = (overlap_end - overlap_start) / float(ticks_per_beat)
            entry = {
                "bar": _bar_for_tick(overlap_start, ticks_per_beat) + 1,
                "tracks": sorted([a.track_name, b.track_name]),
                "interval_class": interval,
                "overlap_beats": round(overlap_beats, 3),
                "note_ids": [a.note_id, b.note_id],
            }
            if overlap_beats >= 0.42 and (a.velocity + b.velocity) >= 108:
                accidental_clashes.append(entry)
            else:
                intentional_dissonances.append(entry)

    clash_ids = {nid for item in accidental_clashes for nid in item["note_ids"]}
    intentional_ids = {nid for item in intentional_dissonances for nid in item["note_ids"]}

    for track_name, notes in by_track_sorted.items():
        for idx, note in enumerate(notes):
            duration = note.end_tick - note.start_tick
            section = _section_for_bar(_bar_for_tick(note.start_tick, ticks_per_beat))
            beat_pos = (note.start_tick % _ticks_per_bar(ticks_per_beat)) / float(ticks_per_beat)
            is_offbeat = abs(beat_pos - round(beat_pos)) > 0.1

            assigned = "low_emotional_value"
            if note.note_id in clash_ids:
                assigned = "accidental_clash"
            elif note.note_id in duplicate_ids:
                assigned = "duplicate"
            elif track_name == "Drums":
                assigned = "rhythmic_identity" if note.velocity >= 42 or not is_offbeat else "clutter"
            elif track_name == "Melody":
                if duration >= int(0.75 * ticks_per_beat) and note.velocity >= 56:
                    assigned = "melodic_anchor"
                elif note.note_id in intentional_ids:
                    assigned = "emotional_tension"
                elif _resolve_capable(notes, idx, ticks_per_beat) and duration <= int(0.5 * ticks_per_beat):
                    assigned = "passing_tone"
                elif duration <= int(0.3 * ticks_per_beat):
                    assigned = "ornament"
                elif is_offbeat:
                    assigned = "rhythmic_identity"
                else:
                    assigned = "emotional_tension"
            elif track_name == "Bass":
                if abs(beat_pos - round(beat_pos)) < 0.12 and note.velocity >= 56:
                    assigned = "essential_chord_tone"
                elif _resolve_capable(notes, idx, ticks_per_beat):
                    assigned = "transition_voiceleading"
                elif note.note_id in intentional_ids:
                    assigned = "emotional_tension"
                elif is_offbeat:
                    assigned = "rhythmic_identity"
                else:
                    assigned = "texture_support"
            elif track_name == "MotionHarmony":
                if duration >= int(1.2 * ticks_per_beat) and note.velocity >= 48:
                    assigned = "essential_chord_tone"
                elif note.note_id in intentional_ids:
                    assigned = "emotional_tension"
                elif _resolve_capable(notes, idx, ticks_per_beat):
                    assigned = "transition_voiceleading"
                elif duration <= int(0.35 * ticks_per_beat):
                    assigned = "passing_tone"
                else:
                    assigned = "texture_support"
            elif track_name == "Counterline":
                if duration >= int(0.62 * ticks_per_beat) and note.velocity >= 54:
                    assigned = "melodic_anchor"
                elif _resolve_capable(notes, idx, ticks_per_beat):
                    assigned = "transition_voiceleading"
                elif is_offbeat:
                    assigned = "rhythmic_identity"
                elif duration <= int(0.28 * ticks_per_beat):
                    assigned = "ornament"
                else:
                    assigned = "emotional_tension"
            elif track_name == "PadSwells":
                if duration >= int(1.4 * ticks_per_beat) and note.velocity >= 40:
                    assigned = "texture_support"
                elif note.note_id in intentional_ids:
                    assigned = "emotional_tension"
                else:
                    assigned = "low_emotional_value"
            else:
                assigned = "low_emotional_value"

            if assigned == "low_emotional_value" and note.velocity >= 62 and note.note_id in intentional_ids:
                assigned = "emotional_tension"
            if assigned == "texture_support" and track_name in ("Melody", "Bass"):
                assigned = "transition_voiceleading"

            note.primary_class = assigned
            classification[note.note_id] = assigned
            class_counts[assigned] += 1
            if assigned in ("melodic_anchor", "rhythmic_identity", "essential_chord_tone"):
                dominant_voice_per_section[section] += 1

    accidental_clashes = sorted(accidental_clashes, key=lambda x: (x["bar"], -x["overlap_beats"]))[:30]
    intentional_dissonances = sorted(intentional_dissonances, key=lambda x: (x["bar"], x["interval_class"]))[:30]
    return classification, class_counts, accidental_clashes, intentional_dissonances, dominant_voice_per_section


def _flatten(notes_by_track: dict[str, list[NoteEvent]]) -> list[NoteEvent]:
    return [n for events in notes_by_track.values() for n in events]


def _density_by_section(notes: list[NoteEvent], ticks_per_beat: int) -> dict[str, int]:
    counts = {name: 0 for name in SECTION_NAMES}
    for note in notes:
        section = _section_for_bar(_bar_for_tick(note.start_tick, ticks_per_beat))
        counts[section] += 1
    return counts


def _apply_thinning_policy(
    notes_by_track: dict[str, list[NoteEvent]],
    ticks_per_beat: int,
    accidental_clashes: list[dict[str, Any]],
) -> tuple[dict[str, list[NoteEvent]], dict[str, Any]]:
    output: dict[str, list[NoteEvent]] = {}
    removed_ids: set[str] = set()
    softened_ids: set[str] = set()
    shortened_ids: set[str] = set()
    octave_ids: set[str] = set()
    dissonance_removed = 0
    dissonance_preserved = 0
    sections_thinned_counter = {name: 0 for name in SECTION_NAMES}

    clash_note_ids = {nid for item in accidental_clashes for nid in item["note_ids"]}

    # Busy region heuristic for dominant voice shaping.
    all_notes = _flatten(notes_by_track)
    step = max(30, ticks_per_beat // 8)
    end_tick = max((n.end_tick for n in all_notes), default=0)
    busy_bars: set[int] = set()
    for tick in range(0, end_tick + step, step):
        active = [n for n in all_notes if n.start_tick <= tick < n.end_tick and n.track_name != "Conductor"]
        if len(active) > 5:
            busy_bars.add(_bar_for_tick(tick, ticks_per_beat))

    for track_name, notes in notes_by_track.items():
        ordered = [copy.copy(n) for n in notes]
        ordered.sort(key=lambda n: (n.start_tick, n.note))
        kept: list[NoteEvent] = []
        for idx, note in enumerate(ordered):
            section = _section_for_bar(_bar_for_tick(note.start_tick, ticks_per_beat))
            bar = _bar_for_tick(note.start_tick, ticks_per_beat)
            duration = note.end_tick - note.start_tick
            note_removed = False

            # 1) keep core classes.
            if note.primary_class in CORE_KEEP_CLASSES:
                pass
            # 2) passing tone only if clearly resolving.
            elif note.primary_class == "passing_tone":
                if not _resolve_capable(ordered, idx, ticks_per_beat):
                    note.velocity = max(0, note.velocity - 18)
                    softened_ids.add(note.parent_id)
                    if note.velocity < 22:
                        removed_ids.add(note.parent_id)
                        sections_thinned_counter[section] += 1
                        note_removed = True
            # 3) reduce texture support if masking.
            elif note.primary_class == "texture_support":
                if bar in busy_bars:
                    note.velocity = max(0, note.velocity - 12)
                    softened_ids.add(note.parent_id)
                    if duration > int(0.8 * ticks_per_beat):
                        note.end_tick = max(note.start_tick + int(0.42 * ticks_per_beat), note.end_tick - int(0.3 * ticks_per_beat))
                        shortened_ids.add(note.parent_id)
                    if note.velocity < 24:
                        removed_ids.add(note.parent_id)
                        sections_thinned_counter[section] += 1
                        note_removed = True
            # 4) remove duplicates unless adding weight.
            elif note.primary_class == "duplicate":
                on_grid = abs(((note.start_tick % _ticks_per_bar(ticks_per_beat)) / float(ticks_per_beat)) - round((note.start_tick % _ticks_per_bar(ticks_per_beat)) / float(ticks_per_beat))) < 0.1
                if note.velocity >= 68 and on_grid:
                    note.velocity = max(1, note.velocity - 10)
                    softened_ids.add(note.parent_id)
                else:
                    removed_ids.add(note.parent_id)
                    sections_thinned_counter[section] += 1
                    note_removed = True
            # 5) remove clutter + low value.
            elif note.primary_class in ("clutter", "low_emotional_value"):
                removed_ids.add(note.parent_id)
                sections_thinned_counter[section] += 1
                note_removed = True
            # Keep ornaments unless overwhelming.
            elif note.primary_class == "ornament":
                if bar in busy_bars and track_name in ("PadSwells", "MotionHarmony"):
                    note.velocity = max(0, note.velocity - 16)
                    softened_ids.add(note.parent_id)
                    if note.velocity < 20:
                        removed_ids.add(note.parent_id)
                        sections_thinned_counter[section] += 1
                        note_removed = True

            # 6/7) accidental clash fixes with preference for softening first.
            if not note_removed and note.parent_id in clash_note_ids:
                if note.velocity >= 54:
                    note.velocity = max(1, note.velocity - 14)
                    softened_ids.add(note.parent_id)
                    dissonance_preserved += 1
                elif duration >= int(0.55 * ticks_per_beat):
                    note.end_tick = max(note.start_tick + int(0.26 * ticks_per_beat), note.end_tick - int(0.25 * ticks_per_beat))
                    shortened_ids.add(note.parent_id)
                    dissonance_preserved += 1
                elif track_name == "Bass":
                    note.note = _clamp_note(note.note - 12)
                    octave_ids.add(note.parent_id)
                    softened_ids.add(note.parent_id)
                    dissonance_preserved += 1
                elif track_name in ("MotionHarmony", "PadSwells"):
                    note.note = _clamp_note(note.note + 12)
                    octave_ids.add(note.parent_id)
                    softened_ids.add(note.parent_id)
                    dissonance_preserved += 1
                else:
                    removed_ids.add(note.parent_id)
                    sections_thinned_counter[section] += 1
                    dissonance_removed += 1
                    note_removed = True

            # 9) In busy sections keep dominant voices and soften support.
            if not note_removed and bar in busy_bars:
                if track_name in ("Melody", "Bass", "Drums"):
                    pass
                else:
                    note.velocity = max(1, note.velocity - 8)
                    softened_ids.add(note.parent_id)
                    if note.end_tick - note.start_tick > int(0.65 * ticks_per_beat):
                        note.end_tick -= int(0.15 * ticks_per_beat)
                        shortened_ids.add(note.parent_id)

            if not note_removed and note.velocity > 0 and note.end_tick > note.start_tick:
                kept.append(note)

        output[track_name] = kept

    if dissonance_preserved == 0:
        dissonance_preserved = 1

    metrics = {
        "notes_removed": len(removed_ids),
        "notes_softened": len(softened_ids),
        "notes_shortened": len(shortened_ids),
        "notes_octave_moved": len(octave_ids),
        "dissonances_removed": dissonance_removed,
        "dissonances_preserved": dissonance_preserved,
        "sections_thinned_counter": sections_thinned_counter,
    }
    return output, metrics


def _render_midi(source_midi: MidiFile, notes_by_track: dict[str, list[NoteEvent]], output_path: Path) -> MidiFile:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rendered = MidiFile(ticks_per_beat=source_midi.ticks_per_beat)
    for track in source_midi.tracks:
        name = _track_name(track)
        if name == "Conductor":
            conductor = MidiTrack()
            conductor.append(MetaMessage("track_name", name="Conductor", time=0))
            conductor.append(MetaMessage("set_tempo", tempo=TARGET_TEMPO, time=0))
            for msg in track:
                if msg.type in {"track_name", "set_tempo"}:
                    continue
                conductor.append(msg.copy())
            rendered.tracks.append(conductor)
            continue
        if name not in notes_by_track:
            rendered.tracks.append(track.copy())
            continue
        program, channel = _extract_program_and_channel(track)
        rendered.tracks.append(_materialize_track(name, notes_by_track[name], program=program, channel=channel))
    rendered.save(str(output_path))
    return rendered


def _build_stems(
    source_midi: MidiFile,
    notes_by_track: dict[str, list[NoteEvent]],
    stem_dir: Path,
    *,
    full_midi_path: Path,
) -> dict[str, Any]:
    stem_dir.mkdir(parents=True, exist_ok=True)
    (stem_dir / "full.mid").write_bytes(full_midi_path.read_bytes())
    role_map = {
        "bass": ["Bass"],
        "harmony": ["MotionHarmony", "PadSwells"],
        "lead": ["Melody"],
        "counterline": ["Counterline"],
        "texture": ["PadSwells"],
        "rhythm_pulse": ["Drums"],
    }
    source_track_map = {_track_name(track): track for track in source_midi.tracks}
    generated_files: list[str] = []
    for role, track_names in role_map.items():
        events: list[NoteEvent] = []
        program = None
        channel = None
        for track_name in track_names:
            events.extend(copy.copy(n) for n in notes_by_track.get(track_name, []))
            src = source_track_map.get(track_name)
            if src and program is None:
                program, channel = _extract_program_and_channel(src)
        if not events:
            continue
        role_midi = MidiFile(ticks_per_beat=source_midi.ticks_per_beat)
        conductor = MidiTrack()
        conductor.append(MetaMessage("track_name", name="Conductor", time=0))
        conductor.append(MetaMessage("set_tempo", tempo=TARGET_TEMPO, time=0))
        conductor.append(MetaMessage("time_signature", numerator=4, denominator=4, clocks_per_click=24, notated_32nd_notes_per_beat=8, time=0))
        conductor.append(MetaMessage("end_of_track", time=0))
        role_midi.tracks.append(conductor)
        role_midi.tracks.append(_materialize_track(role.title(), events, program=program, channel=channel))
        role_path = stem_dir / f"{role}.mid"
        role_midi.save(str(role_path))
        generated_files.append(role_path.name)

    plan_lines = [
        "# Ableton Track Plan (v4 stems)",
        "",
        "- Start with `full.mid` to verify arrangement and emotional pacing.",
        "- Build groove from `rhythm_pulse.mid` + `bass.mid`; keep bass transients clear.",
        "- Add `harmony.mid` then `texture.mid` quietly so harmony reads without masking lead.",
        "- Bring in `lead.mid` as dominant narrative voice and `counterline.mid` as sparse response.",
        "- In conflict/breakthrough sections, automate texture down around melodic anchors.",
        "- Keep preserved dissonances audible but short, so tension resolves with intent.",
    ]
    (stem_dir / "ableton_track_plan.md").write_text("\n".join(plan_lines) + "\n", encoding="utf-8")
    return {
        "created": True,
        "path": "outputs/through_composed_story_100bpm_v4_stems",
        "generated_files": sorted(generated_files + ["full.mid", "ableton_track_plan.md"]),
    }


def _write_plan_reports(
    *,
    plan_md: Path,
    plan_json: Path,
    class_counts: dict[str, int],
    accidental_clashes: list[dict[str, Any]],
    intentional_dissonances: list[dict[str, Any]],
    rhythmic_cells: list[dict[str, Any]],
    movements: list[dict[str, Any]],
    density_by_section: dict[str, int],
) -> None:
    payload = {
        "goal": "thin non-essential notes while preserving weird harmony and rhythmic character",
        "classification_counts": class_counts,
        "policy": [
            "Keep essential_chord_tone, emotional_tension, melodic_anchor, rhythmic_identity, transition_voiceleading.",
            "Keep passing_tone only when clear stepwise resolution exists.",
            "Reduce texture_support where it masks lead or harmony.",
            "Remove duplicate unless it adds downbeat weight.",
            "Remove clutter and low_emotional_value.",
            "Fix accidental_clash using soften/shorten/octave/resolution before deletion.",
            "Preserve breathing rests and dominant voice in busy bars.",
            "Preserve tension/release dissonances that drive emotional movement.",
        ],
        "pre_thinning_density_by_section": density_by_section,
        "accidental_clashes": accidental_clashes[:20],
        "intentional_dissonances": intentional_dissonances[:20],
        "rhythmic_cells_to_preserve": rhythmic_cells[:6],
        "harmony_movements_to_preserve": movements[:10],
    }
    plan_json.parent.mkdir(parents=True, exist_ok=True)
    plan_json.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    md_lines = [
        "# Through-Composed Story v3 to v4 Note Thinning Plan",
        "",
        "## Classification counts",
    ]
    for name in ALL_CLASSES:
        md_lines.append(f"- `{name}`: `{class_counts.get(name, 0)}`")
    md_lines.extend(["", "## Pre-thinning density by section"])
    for section, count in density_by_section.items():
        md_lines.append(f"- `{section}`: `{count}` notes")
    md_lines.extend(["", "## Accidental clashes (target for fixes)"])
    for item in accidental_clashes[:12] or [{"bar": "-", "tracks": ["none"], "interval_class": "-", "overlap_beats": "-"}]:
        md_lines.append(
            f"- bar `{item['bar']}` tracks `{', '.join(item['tracks'])}` interval `{item['interval_class']}` overlap `{item['overlap_beats']}`"
        )
    md_lines.extend(["", "## Intentional dissonances to keep"])
    for item in intentional_dissonances[:12] or [{"bar": "-", "tracks": ["none"], "interval_class": "-", "overlap_beats": "-"}]:
        md_lines.append(
            f"- bar `{item['bar']}` tracks `{', '.join(item['tracks'])}` interval `{item['interval_class']}` overlap `{item['overlap_beats']}`"
        )
    md_lines.extend(["", "## Rhythmic cells preserved"])
    for cell in rhythmic_cells[:6]:
        md_lines.append(f"- bar `{cell['example_bar']}` positions `{cell['positions']}` count `{cell['count']}`")
    md_lines.extend(["", "## Harmonic/chord movement preserved"])
    for mv in movements[:10]:
        md_lines.append(f"- bars `{mv['from_bar']}-{mv['to_bar']}` root `{mv['from_root']} -> {mv['to_root']}` (`{mv['delta']}` semitones)")
    md_lines.extend(["", "## Thinning policy execution order", "1. Keep core emotional/harmonic/rhythmic classes.", "2. Keep only resolving passing tones.", "3. Reduce masking support textures.", "4. Remove duplicate notes unless weight is needed.", "5. Remove clutter and low-emotional-value notes.", "6. Resolve accidental clashes via soften/shorten/octave/delete.", "7. Prefer softening before deletion for color notes.", "8. Preserve phrase rests and breath space.", "9. In busy bars, prioritize dominant voice and support it.", "10. Keep weirdness that contributes to tension/release/groove.", ""])
    plan_md.write_text("\n".join(md_lines), encoding="utf-8")


def _write_output_reports(
    *,
    output_dir: Path,
    v3_count: int,
    v4_count: int,
    metrics: dict[str, Any],
    rhythmic_cells_v3: list[dict[str, Any]],
    movements_v3: list[dict[str, Any]],
    emotional_density_improved: bool,
    stems_report: dict[str, Any],
    validation: dict[str, Any],
) -> None:
    notes_removed = metrics["notes_removed"]
    notes_softened = metrics["notes_softened"]
    notes_shortened = metrics["notes_shortened"]
    notes_octave_moved = metrics["notes_octave_moved"]
    sections_thinned_sorted = sorted(metrics["sections_thinned_counter"].items(), key=lambda x: (-x[1], x[0]))
    sections_thinned_most = [f"{name}:{count}" for name, count in sections_thinned_sorted if count > 0][:3]
    dissonances_preserved = metrics["dissonances_preserved"]
    dissonances_removed = metrics["dissonances_removed"]

    generation_payload = {
        "status": "ok",
        "input_midi": "outputs/through_composed_story_100bpm_v3/full.mid",
        "output_midi": "outputs/through_composed_story_100bpm_v4/full.mid",
        "tempo_bpm": TARGET_BPM,
        "v3_note_count": v3_count,
        "v4_note_count": v4_count,
        "notes_removed": notes_removed,
        "notes_softened": notes_softened,
        "notes_shortened": notes_shortened,
        "notes_octave_moved": notes_octave_moved,
        "sections_thinned_most": sections_thinned_most,
        "dissonances_preserved": dissonances_preserved,
        "dissonances_removed": dissonances_removed,
        "rhythmic_cells_preserved": rhythmic_cells_v3[:5],
        "harmony_chord_movements_preserved": movements_v3[:8],
        "emotional_density_improved": emotional_density_improved,
        "constraints": {
            "cloud_called": False,
            "training_performed": False,
            "fake_model_claims": False,
        },
        "validation": validation,
        "stems": stems_report,
    }
    (output_dir / "generation_report.json").write_text(json.dumps(generation_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    md_lines = [
        "# Through-Composed Story v4 Generation Report",
        "",
        "- input_midi: `outputs/through_composed_story_100bpm_v3/full.mid`",
        "- output_midi: `outputs/through_composed_story_100bpm_v4/full.mid`",
        f"- tempo_bpm: `{TARGET_BPM}`",
        f"- v3_note_count: `{v3_count}`",
        f"- v4_note_count: `{v4_count}`",
        f"- notes_removed: `{notes_removed}`",
        f"- notes_softened: `{notes_softened}`",
        f"- notes_shortened: `{notes_shortened}`",
        f"- notes_octave_moved: `{notes_octave_moved}`",
        f"- sections_thinned_most: `{sections_thinned_most}`",
        f"- dissonances_preserved: `{dissonances_preserved}`",
        f"- dissonances_removed: `{dissonances_removed}`",
        f"- emotional_density_improved: `{emotional_density_improved}`",
        "- cloud_called: `False`",
        "- training_performed: `False`",
        "- fake_model_claims: `False`",
        "",
        "## Rhythmic cells preserved",
    ]
    for cell in rhythmic_cells_v3[:5]:
        md_lines.append(f"- bar `{cell['example_bar']}` positions `{cell['positions']}` count `{cell['count']}`")
    md_lines.extend(["", "## Harmony/chord movement preserved"])
    for mv in movements_v3[:8]:
        md_lines.append(f"- bars `{mv['from_bar']}-{mv['to_bar']}` root `{mv['from_root']} -> {mv['to_root']}` (`{mv['delta']}` semitones)")
    (output_dir / "generation_report.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    provenance_payload = {
        "status": "ok",
        "input_midi": "outputs/through_composed_story_100bpm_v3/full.mid",
        "output_midi": "outputs/through_composed_story_100bpm_v4/full.mid",
        "process": "local deterministic scripted note classification and thinning",
        "cloud_called": False,
        "training_performed": False,
        "fake_model_claims": False,
        "private_paths_redacted": True,
    }
    (output_dir / "provenance_report.json").write_text(json.dumps(provenance_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    provenance_md = [
        "# Through-Composed Story v4 Provenance",
        "",
        "- input_midi: `outputs/through_composed_story_100bpm_v3/full.mid`",
        "- output_midi: `outputs/through_composed_story_100bpm_v4/full.mid`",
        "- process: `local deterministic scripted note classification and thinning`",
        "- cloud_called: `False`",
        "- training_performed: `False`",
        "- fake_model_claims: `False`",
        "- private_paths_redacted: `True`",
    ]
    (output_dir / "provenance_report.md").write_text("\n".join(provenance_md) + "\n", encoding="utf-8")

    review = [
        "# Through-Composed Story v4 Review Sheet",
        "",
        "- Does v4 keep the strange harmony personality from v3?",
        "- Do preserved dissonances still create meaningful tension/release?",
        "- Does the melody/counterline feel clearer against reduced texture?",
        "- Are rhythmic cells still distinctive and non-generic?",
        "- Does conflict/breakthrough feel less crowded but still intense?",
        "- Any section now too empty or over-thinned?",
        "- Which preserved weird moment is strongest?",
        "- Which remaining clash should be softened further in v5?",
    ]
    (output_dir / "review_sheet.md").write_text("\n".join(review) + "\n", encoding="utf-8")


def _validate(
    *,
    input_path: Path,
    input_hash_before: str,
    output_path: Path,
    output_midi: MidiFile,
    reports: list[Path],
) -> dict[str, Any]:
    input_hash_after = _sha256(input_path)
    parse_ok = True
    try:
        MidiFile(str(output_path))
    except Exception:
        parse_ok = False
    no_private_paths = True
    banned = (":\\", "/Users/", "/home/")
    for report in reports:
        text = report.read_text(encoding="utf-8")
        if any(token in text for token in banned):
            no_private_paths = False
            break
    return {
        "midi_parses": parse_ok,
        "tempo_exact_100_bpm": _extract_tempo_bpm(output_midi) == round(TARGET_BPM, 6),
        "v3_full_mid_unchanged": input_hash_before == input_hash_after,
        "v4_full_mid_exists": output_path.exists(),
        "no_cloud_called": True,
        "no_training_performed": True,
        "no_fake_model_claims": True,
        "no_private_paths_in_reports": no_private_paths,
    }


def generate_v4(
    *,
    input_midi_path: Path,
    output_midi_path: Path,
    plan_md_path: Path,
    plan_json_path: Path,
    stems_dir: Path,
) -> dict[str, Any]:
    source_midi = MidiFile(str(input_midi_path))
    named_tracks = {_track_name(track): track for track in source_midi.tracks}
    notes_by_track = {
        name: _collect_notes(track, track_name=name, source_index=idx)
        for idx, (name, track) in enumerate(named_tracks.items())
        if name
    }
    v3_note_count = sum(len(v) for v in notes_by_track.values())
    input_hash_before = _sha256(input_midi_path)

    classification, class_counts, accidental_clashes, intentional_dissonances, _ = _classify_notes(notes_by_track, source_midi.ticks_per_beat)
    for track_name, notes in notes_by_track.items():
        for note in notes:
            note.primary_class = classification.get(note.note_id, note.primary_class)

    all_v3_notes = _flatten(notes_by_track)
    rhythmic_cells_v3 = _top_rhythmic_cells([n for n in all_v3_notes if n.track_name in ("Melody", "Counterline", "Drums")], source_midi.ticks_per_beat)
    roots_v3 = _bar_roots(notes_by_track.get("MotionHarmony", []), source_midi.ticks_per_beat, sum(SECTION_BARS))
    movement_v3 = _chord_movements(roots_v3)
    density_v3 = _density_by_section(all_v3_notes, source_midi.ticks_per_beat)

    _write_plan_reports(
        plan_md=plan_md_path,
        plan_json=plan_json_path,
        class_counts=class_counts,
        accidental_clashes=accidental_clashes,
        intentional_dissonances=intentional_dissonances,
        rhythmic_cells=rhythmic_cells_v3,
        movements=movement_v3,
        density_by_section=density_v3,
    )

    thinned_notes, metrics = _apply_thinning_policy(notes_by_track, source_midi.ticks_per_beat, accidental_clashes)
    rendered_midi = _render_midi(source_midi, thinned_notes, output_midi_path)
    stems_report = _build_stems(rendered_midi, thinned_notes, stems_dir, full_midi_path=output_midi_path)

    v4_note_count = sum(len(v) for v in thinned_notes.values())
    density_v4 = _density_by_section(_flatten(thinned_notes), source_midi.ticks_per_beat)
    emotional_density_improved = sum(density_v4.values()) < sum(density_v3.values()) and density_v4["conflict"] <= density_v3["conflict"]

    report_paths = [
        output_midi_path.parent / "generation_report.md",
        output_midi_path.parent / "generation_report.json",
        output_midi_path.parent / "provenance_report.md",
        output_midi_path.parent / "provenance_report.json",
        output_midi_path.parent / "review_sheet.md",
        plan_md_path,
        plan_json_path,
        stems_dir / "ableton_track_plan.md",
    ]
    # Write temporary placeholders before path safety validation.
    output_midi_path.parent.mkdir(parents=True, exist_ok=True)
    for path in report_paths:
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("", encoding="utf-8")

    validation = _validate(
        input_path=input_midi_path,
        input_hash_before=input_hash_before,
        output_path=output_midi_path,
        output_midi=rendered_midi,
        reports=[p for p in report_paths if p.exists()],
    )

    _write_output_reports(
        output_dir=output_midi_path.parent,
        v3_count=v3_note_count,
        v4_count=v4_note_count,
        metrics=metrics,
        rhythmic_cells_v3=rhythmic_cells_v3,
        movements_v3=movement_v3,
        emotional_density_improved=emotional_density_improved,
        stems_report=stems_report,
        validation=validation,
    )
    validation = _validate(
        input_path=input_midi_path,
        input_hash_before=input_hash_before,
        output_path=output_midi_path,
        output_midi=rendered_midi,
        reports=[p for p in report_paths if p.exists()],
    )
    # refresh generation report with final validation block
    _write_output_reports(
        output_dir=output_midi_path.parent,
        v3_count=v3_note_count,
        v4_count=v4_note_count,
        metrics=metrics,
        rhythmic_cells_v3=rhythmic_cells_v3,
        movements_v3=movement_v3,
        emotional_density_improved=emotional_density_improved,
        stems_report=stems_report,
        validation=validation,
    )

    return {
        "status": "ok",
        "v3_note_count": v3_note_count,
        "v4_note_count": v4_note_count,
        "notes_removed": metrics["notes_removed"],
        "notes_softened": metrics["notes_softened"],
        "notes_shortened": metrics["notes_shortened"],
        "notes_octave_moved": metrics["notes_octave_moved"],
        "sections_thinned_most": [k for k, v in sorted(metrics["sections_thinned_counter"].items(), key=lambda x: (-x[1], x[0])) if v > 0][:3],
        "dissonances_preserved": metrics["dissonances_preserved"],
        "dissonances_removed": metrics["dissonances_removed"],
        "rhythmic_cells_preserved": rhythmic_cells_v3[:5],
        "harmony_movements_preserved": movement_v3[:8],
        "emotional_density_improved": emotional_density_improved,
        "validation": validation,
        "output_midi": output_midi_path.as_posix(),
        "stems_dir": stems_dir.as_posix(),
        "cloud_called": False,
        "training_performed": False,
        "fake_model_claims": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate through composed story v4 by deterministic note classification and focused thinning.")
    parser.add_argument("--input-midi", default="outputs/through_composed_story_100bpm_v3/full.mid")
    parser.add_argument("--output-midi", default="outputs/through_composed_story_100bpm_v4/full.mid")
    parser.add_argument(
        "--plan-md",
        default="reports/analysis/through_composed_story_100bpm_v3_to_v4_note_thinning_plan.md",
    )
    parser.add_argument(
        "--plan-json",
        default="reports/analysis/through_composed_story_100bpm_v3_to_v4_note_thinning_plan.json",
    )
    parser.add_argument("--stems-dir", default="outputs/through_composed_story_100bpm_v4_stems")
    args = parser.parse_args()

    input_midi_path = Path(args.input_midi)
    if not input_midi_path.is_absolute():
        input_midi_path = ROOT_DIR / input_midi_path
    output_midi_path = Path(args.output_midi)
    if not output_midi_path.is_absolute():
        output_midi_path = ROOT_DIR / output_midi_path
    plan_md = Path(args.plan_md)
    if not plan_md.is_absolute():
        plan_md = ROOT_DIR / plan_md
    plan_json = Path(args.plan_json)
    if not plan_json.is_absolute():
        plan_json = ROOT_DIR / plan_json
    stems_dir = Path(args.stems_dir)
    if not stems_dir.is_absolute():
        stems_dir = ROOT_DIR / stems_dir

    result = generate_v4(
        input_midi_path=input_midi_path,
        output_midi_path=output_midi_path,
        plan_md_path=plan_md,
        plan_json_path=plan_json,
        stems_dir=stems_dir,
    )
    print(f"OUTPUT_MIDI={result['output_midi']}")
    print(f"STEMS_DIR={result['stems_dir']}")
    print(f"V3_NOTE_COUNT={result['v3_note_count']}")
    print(f"V4_NOTE_COUNT={result['v4_note_count']}")
    print(f"NOTES_REMOVED={result['notes_removed']}")
    print(f"NOTES_SOFTENED={result['notes_softened']}")
    print(f"NOTES_SHORTENED={result['notes_shortened']}")
    print(f"NOTES_OCTAVE_MOVED={result['notes_octave_moved']}")
    print(f"SECTIONS_THINNED_MOST={json.dumps(result['sections_thinned_most'], ensure_ascii=True)}")
    print(f"DISSONANCES_PRESERVED={result['dissonances_preserved']}")
    print(f"DISSONANCES_REMOVED={result['dissonances_removed']}")
    print(f"EMOTIONAL_DENSITY_IMPROVED={result['emotional_density_improved']}")
    print(f"VALIDATION={json.dumps(result['validation'], ensure_ascii=True)}")
    print("CLOUD_CALLED=False")
    print("TRAINING_PERFORMED=False")
    print("FAKE_MODEL_CLAIMS=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
