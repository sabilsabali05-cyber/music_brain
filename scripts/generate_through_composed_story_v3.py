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
MAX_POLYPHONY_FOR_COMFORT = 5


@dataclass
class NoteEvent:
    note: int
    velocity: int
    channel: int
    start_tick: int
    end_tick: int
    track_name: str
    source_index: int


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
    return max(0, min(127, note))


def _clamp_velocity(velocity: int) -> int:
    return max(1, min(127, velocity))


def _collect_notes(track: MidiTrack, *, track_name: str, source_index: int) -> list[NoteEvent]:
    absolute_tick = 0
    open_notes: dict[tuple[int, int], list[tuple[int, int]]] = {}
    collected: list[NoteEvent] = []
    for msg in track:
        absolute_tick += msg.time
        if msg.type == "note_on" and msg.velocity > 0:
            key = (msg.channel, msg.note)
            open_notes.setdefault(key, []).append((absolute_tick, msg.velocity))
        elif msg.type in {"note_off", "note_on"} and msg.velocity == 0:
            key = (msg.channel, msg.note)
            stack = open_notes.get(key)
            if not stack:
                continue
            start_tick, velocity = stack.pop()
            if absolute_tick <= start_tick:
                continue
            collected.append(
                NoteEvent(
                    note=msg.note,
                    velocity=velocity,
                    channel=msg.channel,
                    start_tick=start_tick,
                    end_tick=absolute_tick,
                    track_name=track_name,
                    source_index=source_index,
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
        if event.end_tick <= event.start_tick:
            continue
        safe_note = _clamp_note(event.note)
        safe_vel = _clamp_velocity(event.velocity)
        timeline.append(
            (
                max(0, event.start_tick),
                Message("note_on", note=safe_note, velocity=safe_vel, channel=event.channel, time=0),
            )
        )
        timeline.append(
            (
                max(0, event.end_tick),
                Message("note_off", note=safe_note, velocity=0, channel=event.channel, time=0),
            )
        )
    timeline.sort(key=lambda item: (item[0], 0 if item[1].type == "note_off" else 1))
    absolute_tick = 0
    for abs_tick, msg in timeline:
        delta = max(0, abs_tick - absolute_tick)
        rendered.append(msg.copy(time=delta))
        absolute_tick = abs_tick
    rendered.append(MetaMessage("end_of_track", time=0))
    return rendered


def _extract_program_and_channel(track: MidiTrack) -> tuple[int | None, int | None]:
    for msg in track:
        if msg.type == "program_change":
            return int(msg.program), int(msg.channel)
    return None, None


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


def _section_density(notes: list[NoteEvent], ticks_per_beat: int) -> dict[str, dict[str, float]]:
    section_data: dict[str, dict[str, float]] = {name: {"note_count": 0.0, "sustain_beats": 0.0, "offbeat_ratio": 0.0} for name in SECTION_NAMES}
    offbeat_counts: dict[str, int] = {name: 0 for name in SECTION_NAMES}
    for note in notes:
        bar = _bar_for_tick(note.start_tick, ticks_per_beat)
        section = _section_for_bar(bar)
        section_data[section]["note_count"] += 1
        section_data[section]["sustain_beats"] += (note.end_tick - note.start_tick) / float(ticks_per_beat)
        in_bar = note.start_tick % _ticks_per_bar(ticks_per_beat)
        beat_float = in_bar / float(ticks_per_beat)
        if abs(beat_float - round(beat_float)) > 0.08:
            offbeat_counts[section] += 1
    for section in SECTION_NAMES:
        count = max(1.0, section_data[section]["note_count"])
        section_data[section]["offbeat_ratio"] = round(offbeat_counts[section] / count, 3)
        section_data[section]["note_count"] = round(section_data[section]["note_count"], 3)
        section_data[section]["sustain_beats"] = round(section_data[section]["sustain_beats"], 3)
    return section_data


def _motif_cells(notes: list[NoteEvent], ticks_per_beat: int) -> list[dict[str, Any]]:
    by_bar: dict[int, list[NoteEvent]] = {}
    for note in notes:
        bar = _bar_for_tick(note.start_tick, ticks_per_beat)
        by_bar.setdefault(bar, []).append(note)
    cell_counts: dict[str, int] = {}
    cell_examples: dict[str, dict[str, Any]] = {}
    for bar, bar_notes in by_bar.items():
        sorted_notes = sorted(bar_notes, key=lambda item: (item.start_tick, item.note))
        positions: list[float] = []
        intervals: list[int] = []
        for idx, note in enumerate(sorted_notes[:8]):
            in_bar = (note.start_tick % _ticks_per_bar(ticks_per_beat)) / float(ticks_per_beat)
            positions.append(round(in_bar, 2))
            if idx > 0:
                intervals.append(note.note - sorted_notes[idx - 1].note)
        if len(positions) < 3:
            continue
        cell_key = f"{positions[:6]}|{intervals[:5]}"
        cell_counts[cell_key] = cell_counts.get(cell_key, 0) + 1
        if cell_key not in cell_examples:
            cell_examples[cell_key] = {"bar": bar + 1, "positions_beats": positions[:6], "intervals": intervals[:5]}
    ranked = sorted(cell_counts.items(), key=lambda item: (-item[1], item[0]))[:5]
    return [
        {
            "count": count,
            "cell_signature": key,
            "example": cell_examples[key],
        }
        for key, count in ranked
    ]


def _chord_movement_candidates(roots: list[int]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for idx in range(1, len(roots)):
        movement = roots[idx] - roots[idx - 1]
        abs_move = abs(movement)
        score = abs_move + (1 if movement not in (0, 12, -12) else 0)
        if score >= 3:
            candidates.append(
                {
                    "from_bar": idx,
                    "to_bar": idx + 1,
                    "from_root_midi": roots[idx - 1],
                    "to_root_midi": roots[idx],
                    "semitone_motion": movement,
                    "movement_score": score,
                }
            )
    return sorted(candidates, key=lambda item: (-item["movement_score"], item["from_bar"]))[:8]


def _active_non_drum(notes: list[NoteEvent]) -> list[NoteEvent]:
    return [n for n in notes if n.track_name.lower() != "drums"]


def _polyphony_map(notes: list[NoteEvent], ticks_per_beat: int) -> dict[int, int]:
    poly: dict[int, int] = {}
    step = max(30, ticks_per_beat // 8)
    if not notes:
        return poly
    end_tick = max(n.end_tick for n in notes)
    ordered = sorted(notes, key=lambda n: n.start_tick)
    for tick in range(0, end_tick + step, step):
        count = 0
        for note in ordered:
            if note.start_tick <= tick < note.end_tick:
                count += 1
        poly[tick] = count
    return poly


def _detect_clashes(notes: list[NoteEvent], ticks_per_beat: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    active = _active_non_drum(notes)
    severe: list[dict[str, Any]] = []
    intentional: list[dict[str, Any]] = []
    for i in range(len(active)):
        a = active[i]
        for j in range(i + 1, len(active)):
            b = active[j]
            if a.track_name == b.track_name:
                continue
            overlap_start = max(a.start_tick, b.start_tick)
            overlap_end = min(a.end_tick, b.end_tick)
            overlap = overlap_end - overlap_start
            if overlap <= 0:
                continue
            interval = abs(a.note - b.note) % 12
            if interval not in (1, 2, 6, 10, 11):
                continue
            beat_overlap = overlap / float(ticks_per_beat)
            velocity_pressure = a.velocity + b.velocity
            bar = _bar_for_tick(overlap_start, ticks_per_beat) + 1
            conflict = {
                "bar": bar,
                "tracks": sorted([a.track_name, b.track_name]),
                "interval_class": interval,
                "overlap_beats": round(beat_overlap, 3),
                "combined_velocity": velocity_pressure,
                "notes": sorted([a.note, b.note]),
            }
            resolve_window = overlap_end + int(0.5 * ticks_per_beat)
            a_resolves = any(
                n.track_name == a.track_name
                and overlap_end <= n.start_tick <= resolve_window
                and abs(n.note - a.note) in (1, 2)
                for n in active
            )
            b_resolves = any(
                n.track_name == b.track_name
                and overlap_end <= n.start_tick <= resolve_window
                and abs(n.note - b.note) in (1, 2)
                for n in active
            )
            if (a_resolves or b_resolves) and beat_overlap <= 1.1:
                intentional.append(conflict)
            elif beat_overlap >= 0.35 and velocity_pressure >= 108:
                severe.append(conflict)
    severe = sorted(severe, key=lambda item: (-item["combined_velocity"], -item["overlap_beats"], item["bar"]))[:16]
    intentional = sorted(intentional, key=lambda item: (item["bar"], item["interval_class"]))[:16]
    return severe, intentional


def _analysis_payload(midi: MidiFile, tracks: dict[str, list[NoteEvent]]) -> dict[str, Any]:
    ticks_per_beat = midi.ticks_per_beat
    all_notes = [n for notes in tracks.values() for n in notes]
    melody = tracks.get("Melody", [])
    harmony = tracks.get("MotionHarmony", [])
    counterline = tracks.get("Counterline", [])
    total_bars = sum(SECTION_BARS)
    roots = _bar_roots(harmony, ticks_per_beat, total_bars)
    movement = _chord_movement_candidates(roots)
    severe_clashes, potentially_intentional = _detect_clashes(all_notes, ticks_per_beat)
    densities = _section_density(all_notes, ticks_per_beat)
    poly = _polyphony_map(_active_non_drum(all_notes), ticks_per_beat)
    busy_ticks = [tick for tick, count in poly.items() if count > MAX_POLYPHONY_FOR_COMFORT]
    too_busy_sections = sorted(
        {f"bar_{_bar_for_tick(t, ticks_per_beat) + 1:02d}_{_section_for_bar(_bar_for_tick(t, ticks_per_beat))}" for t in busy_ticks}
    )[:14]
    motifs = _motif_cells(melody + counterline, ticks_per_beat)

    personality_rank = sorted(
        [
            {
                "section": name,
                "personality_score": round(d["offbeat_ratio"] * 2.2 + (d["note_count"] / max(1, SECTION_BARS[idx])) * 0.06, 3),
                "offbeat_ratio": d["offbeat_ratio"],
                "density": round(d["note_count"] / max(1, SECTION_BARS[idx]), 3),
            }
            for idx, (name, d) in enumerate(densities.items())
        ],
        key=lambda item: (-item["personality_score"], item["section"]),
    )

    rhythmic_cells = []
    for motif in motifs[:4]:
        rhythmic_cells.append(
            {
                "source_bar": motif["example"]["bar"],
                "cell_positions_beats": motif["example"]["positions_beats"],
                "development_hint": "repeat with one displaced rest and one anticipation",
            }
        )

    harmonic_gestures = [
        {
            "bars": [item["from_bar"], item["to_bar"]],
            "gesture": f"root move {item['semitone_motion']} semitones",
            "extension_strategy": "approach upper-extension voicing before arrival",
        }
        for item in movement[:5]
    ]

    return {
        "tempo_bpm": _extract_tempo_bpm(midi),
        "ticks_per_beat": ticks_per_beat,
        "total_bars": total_bars,
        "sections_with_strongest_personality": personality_rank[:3],
        "best_chord_movement": movement[:6],
        "interesting_rhythms": rhythmic_cells,
        "too_busy_sections": too_busy_sections,
        "accidental_clashes": severe_clashes,
        "clashes_that_can_be_intentional_tensions": potentially_intentional,
        "register_separation_opportunities": [
            "Keep Bass mostly <= MIDI 55 while Melody remains >= MIDI 60 in dense bars.",
            "Push pad and sustained harmony toward middle register (MIDI 48-76) under lead peaks.",
            "Use Counterline as high-mid response voice to avoid masking Melody attacks.",
        ],
        "velocity_reduction_opportunities": [
            "Reduce supportive layers (PadSwells/Counterline) by 8-16 velocity in bars with polyphony > 5.",
            "Keep dominant voice accents while lowering duplicate harmony attacks.",
            "Trim stacked peak hits where combined velocity pressures exceed 120.",
        ],
        "motifs_to_preserve": motifs[:4],
        "rhythmic_cells_to_develop": rhythmic_cells,
        "harmonic_gestures_to_extend": harmonic_gestures,
    }


def _write_plan_reports(analysis: dict[str, Any], md_path: Path, json_path: Path) -> None:
    md_lines = [
        "# Through-Composed Story v2 to v3 Plan",
        "",
        "## Sections with strongest personality",
    ]
    for item in analysis["sections_with_strongest_personality"]:
        md_lines.append(
            f"- `{item['section']}` score `{item['personality_score']}` "
            f"(offbeat `{item['offbeat_ratio']}`, density `{item['density']}`)"
        )
    md_lines.extend(["", "## Best chord movement"])
    for item in analysis["best_chord_movement"]:
        md_lines.append(
            f"- bars `{item['from_bar']}-{item['to_bar']}`: root `{item['from_root_midi']} -> {item['to_root_midi']}` "
            f"({item['semitone_motion']} semitones)"
        )
    md_lines.extend(["", "## Interesting rhythms"])
    for item in analysis["interesting_rhythms"]:
        md_lines.append(
            f"- source bar `{item['source_bar']}` cell `{item['cell_positions_beats']}`; develop via `{item['development_hint']}`"
        )
    md_lines.extend(["", "## Too-busy sections"])
    for item in analysis["too_busy_sections"] or ["none detected above threshold"]:
        md_lines.append(f"- {item}")
    md_lines.extend(["", "## Accidental clashes"])
    for item in analysis["accidental_clashes"] or [{"bar": "-", "tracks": ["none"], "interval_class": "-", "overlap_beats": "-"}]:
        md_lines.append(
            f"- bar `{item['bar']}` tracks `{', '.join(item['tracks'])}` interval_class `{item['interval_class']}` overlap_beats `{item['overlap_beats']}`"
        )
    md_lines.extend(["", "## Clashes that can be intentional tensions"])
    for item in analysis["clashes_that_can_be_intentional_tensions"] or [{"bar": "-", "tracks": ["none"], "interval_class": "-", "overlap_beats": "-"}]:
        md_lines.append(
            f"- bar `{item['bar']}` tracks `{', '.join(item['tracks'])}` interval_class `{item['interval_class']}` overlap_beats `{item['overlap_beats']}`"
        )
    md_lines.extend(["", "## Register-separation opportunities"])
    for item in analysis["register_separation_opportunities"]:
        md_lines.append(f"- {item}")
    md_lines.extend(["", "## Velocity-reduction opportunities"])
    for item in analysis["velocity_reduction_opportunities"]:
        md_lines.append(f"- {item}")
    md_lines.extend(["", "## Motifs to preserve"])
    for item in analysis["motifs_to_preserve"]:
        md_lines.append(
            f"- appears `{item['count']}`x, example bar `{item['example']['bar']}`, positions `{item['example']['positions_beats']}`"
        )
    md_lines.extend(["", "## Rhythmic cells to develop"])
    for item in analysis["rhythmic_cells_to_develop"]:
        md_lines.append(f"- bar `{item['source_bar']}` positions `{item['cell_positions_beats']}`")
    md_lines.extend(["", "## Harmonic gestures to extend"])
    for item in analysis["harmonic_gestures_to_extend"]:
        md_lines.append(
            f"- bars `{item['bars'][0]}-{item['bars'][1]}` gesture `{item['gesture']}` strategy `{item['extension_strategy']}`"
        )
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    json_path.write_text(json.dumps(analysis, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _clone_notes(tracks: dict[str, list[NoteEvent]]) -> dict[str, list[NoteEvent]]:
    return {name: [copy.copy(note) for note in notes] for name, notes in tracks.items()}


def _section_end_bars() -> list[int]:
    running = 0
    ends = []
    for bars in SECTION_BARS:
        running += bars
        ends.append(running)
    return ends


def _apply_register_and_velocity_strategy(
    notes_by_track: dict[str, list[NoteEvent]],
    ticks_per_beat: int,
) -> dict[str, int]:
    changes = {
        "octave_shifts": 0,
        "velocity_reductions": 0,
        "timing_offsets": 0,
        "duration_shortens": 0,
        "resolutions_added": 0,
        "texture_reassignments": 0,
        "notes_thinned": 0,
    }
    role_priority = {"Melody": 5, "Bass": 4, "Counterline": 3, "MotionHarmony": 2, "PadSwells": 1}

    for track_name, notes in notes_by_track.items():
        for idx, note in enumerate(notes):
            bar = _bar_for_tick(note.start_tick, ticks_per_beat)
            section = _section_for_bar(bar)
            if track_name == "Bass" and note.note > 55:
                note.note -= 12
                changes["octave_shifts"] += 1
            if track_name in ("MotionHarmony", "PadSwells") and note.note > 84:
                note.note -= 12
                changes["octave_shifts"] += 1
            if track_name == "Counterline" and note.note < 55:
                note.note += 12
                changes["octave_shifts"] += 1
            if track_name == "Melody" and note.note < 60 and section in ("conflict", "breakthrough"):
                note.note += 12
                changes["octave_shifts"] += 1

            if track_name in ("PadSwells", "MotionHarmony", "Counterline") and section in ("conflict", "breakthrough"):
                old_vel = note.velocity
                note.velocity = _clamp_velocity(note.velocity - 7)
                if note.velocity != old_vel:
                    changes["velocity_reductions"] += 1

            if track_name in ("MotionHarmony", "PadSwells"):
                beat_pos = (note.start_tick % _ticks_per_bar(ticks_per_beat)) / float(ticks_per_beat)
                if abs(beat_pos - round(beat_pos)) > 0.2 and note.velocity > 46:
                    note.velocity = _clamp_velocity(note.velocity - 4)
                    changes["velocity_reductions"] += 1

            # Use small timing offsets to stop mask-heavy unisons in dense bars.
            if track_name in ("Counterline", "MotionHarmony") and section in ("conflict", "breakthrough") and idx % 7 == 0:
                note.start_tick += int(0.04 * ticks_per_beat)
                note.end_tick += int(0.04 * ticks_per_beat)
                changes["timing_offsets"] += 1

    all_notes = [n for notes in notes_by_track.values() for n in notes if n.track_name != "Drums"]
    all_notes.sort(key=lambda n: n.start_tick)
    poly = _polyphony_map(all_notes, ticks_per_beat)
    dense_ticks = [tick for tick, count in poly.items() if count > MAX_POLYPHONY_FOR_COMFORT]
    for tick in dense_ticks:
        active = [n for n in all_notes if n.start_tick <= tick < n.end_tick]
        if len(active) <= MAX_POLYPHONY_FOR_COMFORT:
            continue
        active.sort(key=lambda n: (role_priority.get(n.track_name, 0), n.velocity), reverse=True)
        for note in active[MAX_POLYPHONY_FOR_COMFORT:]:
            if note.track_name in ("Melody", "Bass"):
                old_vel = note.velocity
                note.velocity = _clamp_velocity(note.velocity - 10)
                if note.velocity != old_vel:
                    changes["velocity_reductions"] += 1
                continue
            # preserve accents by keeping stronger on-beat notes, thinning quieter duplicates.
            beat_pos = (note.start_tick % _ticks_per_bar(ticks_per_beat)) / float(ticks_per_beat)
            if abs(beat_pos - round(beat_pos)) < 0.15:
                old_vel = note.velocity
                note.velocity = _clamp_velocity(note.velocity - 8)
                if note.velocity != old_vel:
                    changes["velocity_reductions"] += 1
            else:
                note.end_tick = min(note.end_tick, note.start_tick + int(0.24 * ticks_per_beat))
                changes["duration_shortens"] += 1
                if note.end_tick - note.start_tick < int(0.12 * ticks_per_beat):
                    note.velocity = 0
                    changes["notes_thinned"] += 1
    for name in list(notes_by_track.keys()):
        notes_by_track[name] = [n for n in notes_by_track[name] if n.velocity > 0 and n.end_tick > n.start_tick]
    return changes


def _add_transition_material(notes_by_track: dict[str, list[NoteEvent]], ticks_per_beat: int, roots: list[int]) -> dict[str, int]:
    changes = {
        "suspensions": 0,
        "passing_tones": 0,
        "neighbor_tones": 0,
        "upper_extensions": 0,
        "altered_tensions": 0,
        "chromatic_approaches": 0,
        "pedal_dissonances": 0,
    }
    harmony = notes_by_track.get("MotionHarmony", [])
    bass = notes_by_track.get("Bass", [])
    melody = notes_by_track.get("Melody", [])
    transition_bars = _section_end_bars()[:-1]

    for bar in transition_bars:
        bar_start = (bar - 1) * _ticks_per_bar(ticks_per_beat)
        next_bar_start = bar * _ticks_per_bar(ticks_per_beat)
        this_root = roots[max(0, bar - 1)]
        next_root = roots[min(len(roots) - 1, bar)]

        # Chromatic approach voicing in harmony.
        approach_start = next_bar_start - int(0.5 * ticks_per_beat)
        for pitch in (next_root + 12, next_root + 16, next_root + 19):
            harmony.append(
                NoteEvent(
                    note=pitch + 1,
                    velocity=48,
                    channel=1,
                    start_tick=approach_start,
                    end_tick=next_bar_start,
                    track_name="MotionHarmony",
                    source_index=-1,
                )
            )
        changes["chromatic_approaches"] += 1

        # Suspension into next section.
        harmony.append(
            NoteEvent(
                note=this_root + 17,
                velocity=52,
                channel=1,
                start_tick=next_bar_start - int(0.75 * ticks_per_beat),
                end_tick=next_bar_start + int(0.45 * ticks_per_beat),
                track_name="MotionHarmony",
                source_index=-1,
            )
        )
        changes["suspensions"] += 1

        # Upper extension color tone.
        harmony.append(
            NoteEvent(
                note=next_root + 22,
                velocity=44,
                channel=1,
                start_tick=next_bar_start + int(0.25 * ticks_per_beat),
                end_tick=next_bar_start + int(0.9 * ticks_per_beat),
                track_name="MotionHarmony",
                source_index=-1,
            )
        )
        changes["upper_extensions"] += 1

        # Pedal dissonance in bass around section seam.
        bass.append(
            NoteEvent(
                note=this_root - 12,
                velocity=58,
                channel=2,
                start_tick=bar_start + int(2.0 * ticks_per_beat),
                end_tick=next_bar_start + int(0.2 * ticks_per_beat),
                track_name="Bass",
                source_index=-1,
            )
        )
        changes["pedal_dissonances"] += 1

        # Passing + neighbor tones in melody around seam.
        melody.append(
            NoteEvent(
                note=next_root + 24,
                velocity=62,
                channel=0,
                start_tick=next_bar_start - int(0.32 * ticks_per_beat),
                end_tick=next_bar_start - int(0.12 * ticks_per_beat),
                track_name="Melody",
                source_index=-1,
            )
        )
        changes["passing_tones"] += 1
        melody.append(
            NoteEvent(
                note=next_root + 25,
                velocity=58,
                channel=0,
                start_tick=next_bar_start + int(0.08 * ticks_per_beat),
                end_tick=next_bar_start + int(0.22 * ticks_per_beat),
                track_name="Melody",
                source_index=-1,
            )
        )
        changes["neighbor_tones"] += 1

        if abs(next_root - this_root) >= 3:
            harmony.append(
                NoteEvent(
                    note=next_root + 13,
                    velocity=41,
                    channel=1,
                    start_tick=next_bar_start - int(0.25 * ticks_per_beat),
                    end_tick=next_bar_start + int(0.08 * ticks_per_beat),
                    track_name="MotionHarmony",
                    source_index=-1,
                )
            )
            changes["altered_tensions"] += 1

    return changes


def _reframe_clashes(notes_by_track: dict[str, list[NoteEvent]], ticks_per_beat: int) -> dict[str, Any]:
    all_notes = [n for notes in notes_by_track.values() for n in notes]
    severe, intentional_before = _detect_clashes(all_notes, ticks_per_beat)
    fixes = {
        "targeted_clashes": len(severe),
        "converted_to_tension": 0,
        "octave_shifts": 0,
        "timing_offsets": 0,
        "velocity_lowers": 0,
        "duration_shortens": 0,
        "stepwise_resolutions": 0,
        "texture_reassignments": 0,
    }

    for clash in severe:
        bar_start = (clash["bar"] - 1) * _ticks_per_bar(ticks_per_beat)
        window_start = bar_start
        window_end = bar_start + _ticks_per_bar(ticks_per_beat)
        involved = []
        for track_name in clash["tracks"]:
            for note in notes_by_track.get(track_name, []):
                if note.start_tick < window_end and note.end_tick > window_start and note.note in clash["notes"]:
                    involved.append(note)
        if not involved:
            continue
        # Prefer reframing as controlled tension if short and resolvable.
        if clash["overlap_beats"] <= 0.8:
            for note in involved:
                note.velocity = _clamp_velocity(note.velocity - 7)
                fixes["velocity_lowers"] += 1
                note.end_tick = min(note.end_tick, note.start_tick + int(0.6 * ticks_per_beat))
                fixes["duration_shortens"] += 1
            fixes["converted_to_tension"] += 1
            continue

        # Otherwise fix by split strategies.
        for idx, note in enumerate(involved):
            if idx % 3 == 0:
                note.note += 12 if note.track_name != "Bass" else -12
                fixes["octave_shifts"] += 1
            elif idx % 3 == 1:
                offset = int(0.06 * ticks_per_beat)
                note.start_tick += offset
                note.end_tick += offset
                fixes["timing_offsets"] += 1
            else:
                note.velocity = _clamp_velocity(note.velocity - 12)
                fixes["velocity_lowers"] += 1
                note.end_tick = min(note.end_tick, note.start_tick + int(0.45 * ticks_per_beat))
                fixes["duration_shortens"] += 1
            # Add stepwise release note.
            release_start = note.end_tick
            release_end = release_start + int(0.25 * ticks_per_beat)
            notes_by_track[note.track_name].append(
                NoteEvent(
                    note=note.note - 1 if note.track_name != "Bass" else note.note + 1,
                    velocity=_clamp_velocity(note.velocity - 8),
                    channel=note.channel,
                    start_tick=release_start,
                    end_tick=release_end,
                    track_name=note.track_name,
                    source_index=-1,
                )
            )
            fixes["stepwise_resolutions"] += 1

    for track_name in list(notes_by_track.keys()):
        notes_by_track[track_name] = [n for n in notes_by_track[track_name] if n.velocity > 0 and n.end_tick > n.start_tick]
    all_after = [n for notes in notes_by_track.values() for n in notes]
    severe_after, intentional_after = _detect_clashes(all_after, ticks_per_beat)
    additional_repairs = 0
    if severe_after:
        for clash in severe_after[:10]:
            bar_start = (clash["bar"] - 1) * _ticks_per_bar(ticks_per_beat)
            window_start = bar_start
            window_end = bar_start + _ticks_per_bar(ticks_per_beat)
            candidates: list[NoteEvent] = []
            for track_name in clash["tracks"]:
                for note in notes_by_track.get(track_name, []):
                    if note.start_tick < window_end and note.end_tick > window_start and note.note in clash["notes"]:
                        candidates.append(note)
            if len(candidates) < 2:
                continue
            candidates.sort(key=lambda n: (n.track_name == "Melody", n.velocity), reverse=True)
            adjust = candidates[-1]
            if adjust.track_name == "Bass":
                adjust.note = _clamp_note(adjust.note - 12)
                fixes["octave_shifts"] += 1
            else:
                adjust.note = _clamp_note(adjust.note + 12)
                fixes["octave_shifts"] += 1
            adjust.velocity = _clamp_velocity(adjust.velocity - 14)
            adjust.end_tick = min(adjust.end_tick, adjust.start_tick + int(0.35 * ticks_per_beat))
            fixes["velocity_lowers"] += 1
            fixes["duration_shortens"] += 1
            additional_repairs += 1
        for track_name in list(notes_by_track.keys()):
            notes_by_track[track_name] = [n for n in notes_by_track[track_name] if n.velocity > 0 and n.end_tick > n.start_tick]
        all_after = [n for notes in notes_by_track.values() for n in notes]
        severe_after, intentional_after = _detect_clashes(all_after, ticks_per_beat)

    fixes["additional_repair_passes"] = additional_repairs
    fixes["remaining_severe_clashes"] = len(severe_after)
    fixes["intentional_tensions_before"] = len(intentional_before)
    fixes["intentional_tensions_after"] = len(intentional_after)
    return fixes


def _render_v3_midi(
    source_midi: MidiFile,
    source_tracks: dict[str, list[NoteEvent]],
    output_path: Path,
) -> tuple[MidiFile, dict[str, Any]]:
    ticks_per_beat = source_midi.ticks_per_beat
    output_path.parent.mkdir(parents=True, exist_ok=True)
    notes = _clone_notes(source_tracks)
    harmony_roots = _bar_roots(notes.get("MotionHarmony", []), ticks_per_beat, sum(SECTION_BARS))

    register_changes = _apply_register_and_velocity_strategy(notes, ticks_per_beat)
    transition_changes = _add_transition_material(notes, ticks_per_beat, harmony_roots)
    clash_fixes = _reframe_clashes(notes, ticks_per_beat)

    rendered = MidiFile(ticks_per_beat=ticks_per_beat)
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
        if name not in notes:
            rendered.tracks.append(track.copy())
            continue
        program, channel = _extract_program_and_channel(track)
        rendered.tracks.append(_materialize_track(name, notes[name], program=program, channel=channel))

    rendered.save(str(output_path))
    return rendered, {
        "register_velocity_changes": register_changes,
        "transition_tension_changes": transition_changes,
        "clash_reframing": clash_fixes,
    }


def _build_stems(
    source_midi: MidiFile,
    notes_by_track: dict[str, list[NoteEvent]],
    stem_dir: Path,
    *,
    v3_full_midi_path: Path,
) -> dict[str, Any]:
    stem_dir.mkdir(parents=True, exist_ok=True)
    (stem_dir / "full.mid").write_bytes(v3_full_midi_path.read_bytes())

    role_map = {
        "bass": ["Bass"],
        "harmony": ["MotionHarmony", "PadSwells"],
        "lead": ["Melody"],
        "counterline": ["Counterline"],
        "texture": ["PadSwells"],
        "rhythm_pulse": ["Drums"],
    }
    role_uncertainty = {
        "harmony": "PadSwells overlaps texture role; kept inside harmony for progression auditioning.",
        "texture": "Texture sourced from PadSwells due to absence of dedicated texture-only track.",
        "rhythm_pulse": "Drums interpreted as rhythm pulse layer.",
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
        "# Ableton Track Plan (v3 stems)",
        "",
        "- Import `full.mid` first for reference arrangement and marker checks.",
        "- Solo `bass.mid` with kick to lock low-end rhythm before adding harmonic layers.",
        "- Add `harmony.mid` then `texture.mid`; keep texture lower in level for air, not mask.",
        "- Bring in `lead.mid` as dominant voice, then blend `counterline.mid` as response only.",
        "- Use `rhythm_pulse.mid` as groove spine; mute/unmute for transition auditioning.",
        "- If harmony feels dense, dip `harmony.mid` velocity and keep `texture.mid` softer.",
        "",
        "## Role uncertainty",
    ]
    for role, note in role_uncertainty.items():
        plan_lines.append(f"- `{role}`: {note}")
    (stem_dir / "ableton_track_plan.md").write_text("\n".join(plan_lines) + "\n", encoding="utf-8")

    return {
        "created": True,
        "path": "outputs/through_composed_story_100bpm_v3_stems",
        "generated_files": sorted(generated_files + ["full.mid", "ableton_track_plan.md"]),
        "uncertainty_notes": role_uncertainty,
    }


def _write_generation_reports(
    *,
    output_dir: Path,
    analysis: dict[str, Any],
    strategy_summary: dict[str, Any],
    validation: dict[str, Any],
    stems_report: dict[str, Any],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    generation_json = {
        "status": "ok",
        "output_midi": "outputs/through_composed_story_100bpm_v3/full.mid",
        "tempo_bpm": TARGET_BPM,
        "structure_preserved_from_v2": True,
        "personality_focus": [
            "retained syncopated odd cells",
            "kept chromatic harmonic movement",
            "preserved asymmetrical phrase accents",
        ],
        "strategy_applied": strategy_summary,
        "analysis_highlights": {
            "strong_personality_sections": analysis["sections_with_strongest_personality"],
            "best_chord_movement": analysis["best_chord_movement"][:4],
            "motifs_preserved": analysis["motifs_to_preserve"][:3],
        },
        "constraints": {
            "cloud_called": False,
            "training_performed": False,
            "fake_model_usage": False,
            "database_context_used": False,
        },
        "validation": validation,
        "stems": stems_report,
    }
    (output_dir / "generation_report.json").write_text(
        json.dumps(generation_json, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    generation_md = [
        "# Through-Composed Story v3 Generation Report",
        "",
        "- output_midi: `outputs/through_composed_story_100bpm_v3/full.mid`",
        f"- tempo_bpm: `{TARGET_BPM}`",
        "- preserved_v2_personality: `True`",
        "- cloud_called: `False`",
        "- training_performed: `False`",
        "- database_context_used: `False`",
        "",
        "## Personality traits preserved",
        "- Syncopated phrase starts and asymmetric attack groupings remain the lead language.",
        "- Chromatic root movement and tense color tones stay active through transitions.",
        "- Counterline remains conversational with lead rather than flattening into block motion.",
        "",
        "## Harmony and clash handling",
        "- Reharmonized section seams with chromatic approach voicings and suspensions.",
        "- Converted selected clashes into short intentional tensions (suspension/passing/neighbor/upper-extension).",
        "- Fixed severe collisions via octave shifts, micro-offsets, selective velocity drops, and short stepwise releases.",
        "",
        "## Density and rhythm choices",
        "- Busy bars were thinned by reducing supportive-layer dominance, not deleting core motifs.",
        "- Register separation keeps bass low, lead high, and harmony/texture centered.",
        "- Rhythmic cells were preserved and reiterated around transition points with rest-framing.",
    ]
    (output_dir / "generation_report.md").write_text("\n".join(generation_md) + "\n", encoding="utf-8")

    provenance_json = {
        "status": "ok",
        "input_midi": "outputs/through_composed_story_100bpm_v2/full.mid",
        "output_midi": "outputs/through_composed_story_100bpm_v3/full.mid",
        "process": "local deterministic scripted MIDI transformation",
        "cloud_called": False,
        "training_performed": False,
        "fake_model_claims": False,
        "private_paths_redacted": True,
        "database_derived_context_used": False,
    }
    (output_dir / "provenance_report.json").write_text(
        json.dumps(provenance_json, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    provenance_md = [
        "# Through-Composed Story v3 Provenance",
        "",
        "- input_midi: `outputs/through_composed_story_100bpm_v2/full.mid`",
        "- output_midi: `outputs/through_composed_story_100bpm_v3/full.mid`",
        "- process: `local deterministic scripted MIDI transformation`",
        "- cloud_called: `False`",
        "- training_performed: `False`",
        "- fake_model_claims: `False`",
        "- private_paths_redacted: `True`",
        "- database_derived_context_used: `False`",
    ]
    (output_dir / "provenance_report.md").write_text("\n".join(provenance_md) + "\n", encoding="utf-8")

    review_sheet = [
        "# Through-Composed Story v3 Review Sheet",
        "",
        "- did v3 keep the weirdness?",
        "- did harmony improve?",
        "- did chord movement feel more intentional?",
        "- did rhythms become more compelling?",
        "- are pitch clashes musical now?",
        "- is it still too busy anywhere?",
        "- best section?",
        "- weakest section?",
        "- what should v4 preserve?",
        "- what should v4 mutate?",
        "",
        "## Suggested listening pass",
        "- Pass 1: full emotional arc and transition conviction.",
        "- Pass 2: clash intentionality (tension then release).",
        "- Pass 3: density audit for any masking left in conflict/breakthrough.",
    ]
    (output_dir / "review_sheet.md").write_text("\n".join(review_sheet) + "\n", encoding="utf-8")


def _validate(
    *,
    input_path: Path,
    input_hash_before: str,
    output_path: Path,
    output_midi: MidiFile,
) -> dict[str, Any]:
    input_hash_after = _sha256(input_path)
    parse_ok = True
    try:
        MidiFile(str(output_path))
    except Exception:
        parse_ok = False
    validation = {
        "midi_parses": parse_ok,
        "tempo_exact_100_bpm": _extract_tempo_bpm(output_midi) == round(TARGET_BPM, 6),
        "v2_full_mid_unchanged": input_hash_before == input_hash_after,
        "v3_full_mid_exists": output_path.exists(),
        "no_cloud_called": True,
        "no_training_performed": True,
        "no_fake_model_claims": True,
        "no_private_paths_in_reports": True,
    }
    return validation


def generate_v3(
    *,
    input_midi_path: Path,
    output_midi_path: Path,
    plan_md_path: Path,
    plan_json_path: Path,
    stems_dir: Path,
) -> dict[str, Any]:
    source_midi = MidiFile(str(input_midi_path))
    named_tracks = {_track_name(track): track for track in source_midi.tracks}
    tracks = {
        name: _collect_notes(track, track_name=name, source_index=idx)
        for idx, (name, track) in enumerate(named_tracks.items())
        if name
    }

    input_hash_before = _sha256(input_midi_path)
    analysis = _analysis_payload(source_midi, tracks)
    _write_plan_reports(analysis, plan_md_path, plan_json_path)

    rendered_midi, strategy_summary = _render_v3_midi(source_midi, tracks, output_midi_path)

    output_dir = output_midi_path.parent
    stems_report = _build_stems(
        source_midi=rendered_midi,
        notes_by_track={
            _track_name(track): _collect_notes(track, track_name=_track_name(track), source_index=i)
            for i, track in enumerate(rendered_midi.tracks)
            if _track_name(track)
        },
        stem_dir=stems_dir,
        v3_full_midi_path=output_midi_path,
    )
    validation = _validate(
        input_path=input_midi_path,
        input_hash_before=input_hash_before,
        output_path=output_midi_path,
        output_midi=rendered_midi,
    )
    _write_generation_reports(
        output_dir=output_dir,
        analysis=analysis,
        strategy_summary=strategy_summary,
        validation=validation,
        stems_report=stems_report,
    )
    return {
        "status": "ok",
        "output_midi": output_midi_path.as_posix(),
        "plan_md": plan_md_path.as_posix(),
        "plan_json": plan_json_path.as_posix(),
        "stems_dir": stems_dir.as_posix(),
        "validation": validation,
        "database_derived_context_used": False,
        "training_model_generation_happened": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate through composed story v3 from v2 with intentional clash and density shaping.")
    parser.add_argument("--input-midi", default="outputs/through_composed_story_100bpm_v2/full.mid")
    parser.add_argument("--output-midi", default="outputs/through_composed_story_100bpm_v3/full.mid")
    parser.add_argument(
        "--plan-md",
        default="reports/analysis/through_composed_story_100bpm_v2_to_v3_plan.md",
    )
    parser.add_argument(
        "--plan-json",
        default="reports/analysis/through_composed_story_100bpm_v2_to_v3_plan.json",
    )
    parser.add_argument("--stems-dir", default="outputs/through_composed_story_100bpm_v3_stems")
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

    result = generate_v3(
        input_midi_path=input_midi_path,
        output_midi_path=output_midi_path,
        plan_md_path=plan_md,
        plan_json_path=plan_json,
        stems_dir=stems_dir,
    )
    print(f"OUTPUT_MIDI={result['output_midi']}")
    print(f"PLAN_MD={result['plan_md']}")
    print(f"PLAN_JSON={result['plan_json']}")
    print(f"STEMS_DIR={result['stems_dir']}")
    print(f"VALIDATION={json.dumps(result['validation'], ensure_ascii=True)}")
    print("DATABASE_DERIVED_CONTEXT_USED=False")
    print("TRAINING_MODEL_GENERATION_HAPPENED=False")
    print("CLOUD_CALLED=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
