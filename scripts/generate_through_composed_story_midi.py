from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from mido import Message, MetaMessage, MidiFile, MidiTrack, bpm2tempo

ROOT_DIR = Path(__file__).resolve().parent.parent
TICKS_PER_BEAT = 480
TARGET_BPM = 100
TEMPO = bpm2tempo(TARGET_BPM)


@dataclass(frozen=True)
class Section:
    name: str
    bars: int
    chord_cycle: tuple[tuple[int, int, int], ...]
    melody_scale: tuple[int, ...]
    melody_center: int
    energy: int


SECTIONS: tuple[Section, ...] = (
    Section(
        name="intro_tension",
        bars=8,
        chord_cycle=((50, 53, 57), (48, 52, 55), (46, 50, 53), (45, 50, 53)),
        melody_scale=(50, 52, 53, 55, 57, 58, 60, 62),
        melody_center=62,
        energy=56,
    ),
    Section(
        name="lift",
        bars=10,
        chord_cycle=((53, 57, 60), (55, 59, 62), (57, 60, 64), (52, 55, 60), (50, 53, 57)),
        melody_scale=(53, 55, 57, 59, 60, 62, 64, 65),
        melody_center=65,
        energy=72,
    ),
    Section(
        name="conflict",
        bars=12,
        chord_cycle=((55, 58, 62), (57, 60, 63), (58, 62, 65), (53, 57, 60), (50, 54, 57), (52, 55, 59)),
        melody_scale=(50, 52, 53, 55, 56, 58, 60, 62, 63, 65),
        melody_center=66,
        energy=84,
    ),
    Section(
        name="breakthrough",
        bars=8,
        chord_cycle=((58, 62, 65), (60, 63, 67), (62, 65, 69), (57, 60, 65)),
        melody_scale=(57, 58, 60, 62, 63, 65, 67, 69),
        melody_center=69,
        energy=78,
    ),
    Section(
        name="resolution",
        bars=10,
        chord_cycle=((50, 54, 57), (48, 52, 55), (50, 53, 57), (52, 55, 59), (50, 54, 57)),
        melody_scale=(50, 52, 54, 55, 57, 59, 61, 62),
        melody_center=64,
        energy=62,
    ),
)


def _beats_to_ticks(beats: float) -> int:
    return int(round(beats * TICKS_PER_BEAT))


def _clamp_note(note: int) -> int:
    return max(0, min(127, note))


def _clamp_velocity(velocity: int) -> int:
    return max(1, min(127, velocity))


def _append_note_event(
    events: list[tuple[int, Message]],
    *,
    start_beats: float,
    duration_beats: float,
    note: int,
    velocity: int,
    channel: int,
) -> None:
    start_tick = _beats_to_ticks(start_beats)
    end_tick = _beats_to_ticks(start_beats + max(0.05, duration_beats))
    safe_note = _clamp_note(note)
    safe_velocity = _clamp_velocity(velocity)
    events.append((start_tick, Message("note_on", note=safe_note, velocity=safe_velocity, channel=channel, time=0)))
    events.append((end_tick, Message("note_off", note=safe_note, velocity=0, channel=channel, time=0)))


def _materialize_track(name: str, program: int | None, events: list[tuple[int, Message]], channel: int | None) -> MidiTrack:
    track = MidiTrack()
    track.append(MetaMessage("track_name", name=name, time=0))
    if program is not None and channel is not None:
        track.append(Message("program_change", program=program, channel=channel, time=0))
    events.sort(key=lambda item: (item[0], 0 if item[1].type == "note_off" else 1))
    current_tick = 0
    for abs_tick, message in events:
        delta = max(0, abs_tick - current_tick)
        track.append(message.copy(time=delta))
        current_tick = abs_tick
    track.append(MetaMessage("end_of_track", time=0))
    return track


def _nearest_scale_tone(note: int, scale: Iterable[int]) -> int:
    scale_list = list(scale)
    return min(scale_list, key=lambda candidate: abs(candidate - note))


def _compose_section(
    section: Section,
    section_start_bar: int,
    melody_events: list[tuple[int, Message]],
    harmony_events: list[tuple[int, Message]],
    bass_events: list[tuple[int, Message]],
    drum_events: list[tuple[int, Message]],
) -> None:
    rhythm_variants = (
        (0.0, 0.75, 0), (0.75, 0.5, 2), (1.5, 0.5, 4), (2.25, 0.75, 3), (3.0, 1.0, 1),
        (0.0, 0.5, 0), (0.5, 0.5, 1), (1.0, 0.75, 3), (1.75, 0.5, 2), (2.5, 0.5, 4), (3.0, 0.75, 5),
        (0.0, 1.0, 0), (1.0, 0.5, 2), (1.5, 0.5, 3), (2.0, 0.75, 4), (2.75, 0.5, 2), (3.25, 0.5, 1),
        (0.0, 0.5, 0), (0.5, 0.75, 2), (1.25, 0.5, 4), (1.75, 0.5, 5), (2.25, 0.75, 3), (3.0, 0.75, 1),
    )
    arp_patterns = (
        (0, 1, 2, 1, 0, 2, 1, 2),
        (0, 2, 1, 2, 0, 1, 2, 1),
        (0, 1, 2, 0, 2, 1, 0, 1),
        (0, 2, 1, 0, 1, 2, 1, 2),
    )
    bass_patterns = (
        ((0.0, 1.5, 0), (1.5, 1.0, 2), (2.5, 1.5, 0)),
        ((0.0, 1.0, 0), (1.0, 1.0, 0), (2.0, 1.0, 2), (3.0, 1.0, 0)),
        ((0.0, 2.0, 0), (2.0, 1.0, 2), (3.0, 1.0, 4)),
    )

    for local_bar in range(section.bars):
        absolute_bar = section_start_bar + local_bar
        chord = section.chord_cycle[local_bar % len(section.chord_cycle)]
        bar_start = absolute_bar * 4.0
        energy = section.energy + (local_bar % 3) * 2

        # Supportive harmony motion via evolving eighth-note arpeggios.
        arp = arp_patterns[(absolute_bar + section.energy) % len(arp_patterns)]
        for step, degree in enumerate(arp):
            beat = bar_start + step * 0.5
            note = chord[degree]
            lift = 12 if step % 2 == 1 else 0
            _append_note_event(
                harmony_events,
                start_beats=beat,
                duration_beats=0.42,
                note=note + lift,
                velocity=max(42, energy - 16 + (step % 3) * 3),
                channel=1,
            )

        # Bass drives the phrase with changing rhythmic figures per bar.
        bass_pattern = bass_patterns[(absolute_bar + len(chord)) % len(bass_patterns)]
        for beat_offset, length, degree in bass_pattern:
            _append_note_event(
                bass_events,
                start_beats=bar_start + beat_offset,
                duration_beats=length * 0.9,
                note=chord[degree % len(chord)] - 12,
                velocity=max(45, energy - 6),
                channel=2,
            )

        # Melody evolves by rotating phrase shapes and contour targets.
        phrase = rhythm_variants[(absolute_bar * 3) % len(rhythm_variants):(absolute_bar * 3) % len(rhythm_variants) + 6]
        if len(phrase) < 6:
            phrase = phrase + rhythm_variants[: 6 - len(phrase)]
        melodic_anchor = section.melody_center + ((local_bar % 5) - 2) * 2
        for beat_offset, dur, contour_idx in phrase:
            contour = (-3, -1, 1, 3, 5, 7, 4, 2, 0, -2)
            raw_note = melodic_anchor + contour[(contour_idx + local_bar) % len(contour)]
            chord_hint = chord[(contour_idx + local_bar) % len(chord)] + 12
            blended = int(round((raw_note * 2 + chord_hint) / 3))
            melody_note = _nearest_scale_tone(blended, section.melody_scale)
            _append_note_event(
                melody_events,
                start_beats=bar_start + beat_offset,
                duration_beats=dur,
                note=melody_note,
                velocity=max(52, energy + 4 - (contour_idx % 3) * 2),
                channel=0,
            )

        # Drum kit dynamics follow section arc and avoid static loops.
        kick_positions = (0.0, 1.5, 2.0, 3.25) if energy >= 75 else (0.0, 2.0, 3.0)
        snare_positions = (1.0, 3.0)
        hat_density = 0.5 if energy >= 70 else 1.0
        for beat in kick_positions:
            _append_note_event(
                drum_events,
                start_beats=bar_start + beat,
                duration_beats=0.08,
                note=36,
                velocity=min(120, energy + 20),
                channel=9,
            )
        for beat in snare_positions:
            _append_note_event(
                drum_events,
                start_beats=bar_start + beat,
                duration_beats=0.08,
                note=38,
                velocity=min(118, energy + 14),
                channel=9,
            )
        hat = 0.0
        while hat < 4.0:
            hat_velocity = max(36, energy - 12 + int((hat * 10) % 5))
            _append_note_event(
                drum_events,
                start_beats=bar_start + hat,
                duration_beats=0.05,
                note=42 if int(hat * 2) % 4 else 46,
                velocity=hat_velocity,
                channel=9,
            )
            hat += hat_density


def generate_story_midi(output_dir: Path) -> dict[str, object]:
    full_path = output_dir / "full.mid"
    output_dir.mkdir(parents=True, exist_ok=True)

    midi = MidiFile(ticks_per_beat=TICKS_PER_BEAT)

    conductor = MidiTrack()
    conductor.append(MetaMessage("track_name", name="Conductor", time=0))
    conductor.append(MetaMessage("set_tempo", tempo=TEMPO, time=0))
    conductor.append(MetaMessage("time_signature", numerator=4, denominator=4, clocks_per_click=24, notated_32nd_notes_per_beat=8, time=0))
    midi.tracks.append(conductor)

    melody_events: list[tuple[int, Message]] = []
    harmony_events: list[tuple[int, Message]] = []
    bass_events: list[tuple[int, Message]] = []
    drum_events: list[tuple[int, Message]] = []

    running_bar = 0
    section_ranges: list[dict[str, object]] = []
    for section in SECTIONS:
        start_bar = running_bar
        _compose_section(section, start_bar, melody_events, harmony_events, bass_events, drum_events)
        running_bar += section.bars
        section_ranges.append(
            {
                "name": section.name,
                "start_bar": start_bar + 1,
                "end_bar": running_bar,
                "bars": section.bars,
            }
        )

    midi.tracks.append(_materialize_track("Melody", program=40, events=melody_events, channel=0))
    midi.tracks.append(_materialize_track("MotionHarmony", program=0, events=harmony_events, channel=1))
    midi.tracks.append(_materialize_track("Bass", program=33, events=bass_events, channel=2))
    midi.tracks.append(_materialize_track("Drums", program=None, events=drum_events, channel=None))

    conductor.append(MetaMessage("end_of_track", time=_beats_to_ticks(running_bar * 4.0)))
    midi.save(str(full_path))

    total_beats = running_bar * 4
    approx_seconds = round(total_beats * (60.0 / TARGET_BPM), 2)
    report = {
        "status": "ok",
        "piece_title": "through_composed_story_100bpm",
        "tempo_bpm": TARGET_BPM,
        "time_signature": "4/4",
        "total_bars": running_bar,
        "approx_duration_seconds": approx_seconds,
        "form_sequence": [section.name for section in SECTIONS],
        "section_layout": section_ranges,
        "harmonic_center_arc": ["D minor", "F major/A minor", "G minor chromatic", "B-flat major", "D minor with Picardy lift"],
        "narrative_arc": "intro tension -> lift -> conflict -> breakthrough -> resolution",
        "texture": ["melody", "arpeggiated harmonic motion", "bass line", "drum groove"],
        "through_composed": True,
        "uses_static_block_chords_only": False,
        "fallback_used": False,
        "cloud_called": False,
        "model_training_used": False,
        "outputs": {
            "midi_file": "full.mid",
            "generation_report_json": "generation_report.json",
            "generation_report_md": "generation_report.md",
        },
    }

    (output_dir / "generation_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    md_lines = [
        "# Through-Composed Story MIDI Report",
        "",
        f"- piece_title: `{report['piece_title']}`",
        f"- tempo_bpm: `{TARGET_BPM}`",
        f"- total_bars: `{running_bar}`",
        f"- approx_duration_seconds: `{approx_seconds}`",
        f"- form_sequence: `{', '.join(report['form_sequence'])}`",
        f"- narrative_arc: `{report['narrative_arc']}`",
        f"- harmonic_center_arc: `{', '.join(report['harmonic_center_arc'])}`",
        f"- through_composed: `{report['through_composed']}`",
        f"- uses_static_block_chords_only: `{report['uses_static_block_chords_only']}`",
        f"- fallback_used: `{report['fallback_used']}`",
        "",
        "## Section Layout",
    ]
    for section in section_ranges:
        md_lines.append(
            f"- `{section['name']}`: bars `{section['start_bar']}-{section['end_bar']}` "
            f"({section['bars']} bars)"
        )
    (output_dir / "generation_report.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a deterministic through-composed narrative MIDI piece.")
    parser.add_argument("--output", default="outputs/through_composed_story_100bpm")
    args = parser.parse_args()

    output_dir = Path(args.output)
    if not output_dir.is_absolute():
        output_dir = ROOT_DIR / output_dir
    report = generate_story_midi(output_dir)
    print(f"OUTPUT_DIR={output_dir.as_posix()}")
    print(f"MIDI_FILE={(output_dir / 'full.mid').as_posix()}")
    print(f"TEMPO_BPM={report['tempo_bpm']}")
    print(f"FORM_SEQUENCE={','.join(report['form_sequence'])}")
    print(f"FALLBACK_USED={report['fallback_used']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
