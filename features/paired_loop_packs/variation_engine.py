from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

VALID_VARIATIONS = (
    "sparse",
    "dense",
    "syncopated",
    "rhythmic_mutation",
    "melodic_mutation",
    "reharmonized",
    "call_response",
    "tension",
    "release",
    "texture_chop",
)


@dataclass(frozen=True)
class MidiNote:
    pitch: int
    velocity: int
    start_tick: int
    duration_tick: int


@dataclass(frozen=True)
class LoopMeta:
    bars: int
    bpm: float
    key: str
    ticks_per_quarter: int = 480

    @property
    def loop_ticks(self) -> int:
        return int(self.bars * 4 * self.ticks_per_quarter)


def clamp_pitch(value: int) -> int:
    return max(24, min(108, int(value)))


def clamp_velocity(value: int) -> int:
    return max(20, min(127, int(value)))


def clamp_duration(value: int) -> int:
    return max(30, int(value))


def sanitize_notes(notes: list[MidiNote], meta: LoopMeta) -> list[MidiNote]:
    out: list[MidiNote] = []
    loop_ticks = meta.loop_ticks
    for note in notes:
        start = max(0, min(note.start_tick, max(0, loop_ticks - 1)))
        dur = clamp_duration(note.duration_tick)
        if start + dur > loop_ticks:
            dur = max(30, loop_ticks - start)
        if dur <= 0:
            continue
        out.append(
            MidiNote(
                pitch=clamp_pitch(note.pitch),
                velocity=clamp_velocity(note.velocity),
                start_tick=start,
                duration_tick=dur,
            )
        )
    out.sort(key=lambda item: (item.start_tick, item.pitch))
    return out


def note_event_hash(notes: list[MidiNote]) -> str:
    chunks = [f"{n.pitch}:{n.velocity}:{n.start_tick}:{n.duration_tick}" for n in notes]
    return "|".join(chunks)


def assert_distinct(seed_notes: list[MidiNote], varied_notes: list[MidiNote], variation_name: str) -> list[MidiNote]:
    if note_event_hash(seed_notes) != note_event_hash(varied_notes):
        return varied_notes
    # Deterministic nudge fallback if a transform accidentally produces a clone.
    nudged = [
        MidiNote(
            pitch=clamp_pitch(note.pitch + (1 if idx % 2 == 0 else -1)),
            velocity=clamp_velocity(note.velocity + 4),
            start_tick=note.start_tick,
            duration_tick=note.duration_tick,
        )
        for idx, note in enumerate(varied_notes)
    ]
    if note_event_hash(seed_notes) == note_event_hash(nudged):
        raise ValueError(f"Variation {variation_name} produced identical MIDI to seed.")
    return nudged


def _sparse(notes: list[MidiNote], meta: LoopMeta) -> list[MidiNote]:
    reduced = [note for idx, note in enumerate(notes) if idx % 2 == 0]
    return sanitize_notes(reduced or notes[:1], meta)


def _dense(notes: list[MidiNote], meta: LoopMeta) -> list[MidiNote]:
    add: list[MidiNote] = []
    for note in notes:
        ghost_start = min(meta.loop_ticks - 1, note.start_tick + max(60, note.duration_tick // 2))
        add.append(
            MidiNote(
                pitch=clamp_pitch(note.pitch + (12 if note.pitch < 72 else -12)),
                velocity=clamp_velocity(note.velocity - 14),
                start_tick=ghost_start,
                duration_tick=max(60, note.duration_tick // 2),
            )
        )
    return sanitize_notes(notes + add, meta)


def _syncopated(notes: list[MidiNote], meta: LoopMeta) -> list[MidiNote]:
    shift = meta.ticks_per_quarter // 2
    out: list[MidiNote] = []
    for idx, note in enumerate(notes):
        if idx % 2 == 0:
            start = note.start_tick
        else:
            start = (note.start_tick + shift) % meta.loop_ticks
        out.append(MidiNote(note.pitch, note.velocity, start, note.duration_tick))
    return sanitize_notes(out, meta)


def _rhythmic_mutation(notes: list[MidiNote], meta: LoopMeta) -> list[MidiNote]:
    out: list[MidiNote] = []
    for idx, note in enumerate(notes):
        if idx % 3 == 0:
            dur = max(60, note.duration_tick // 2)
        elif idx % 3 == 1:
            dur = min(meta.ticks_per_quarter * 2, int(note.duration_tick * 1.5))
        else:
            dur = note.duration_tick
        offset = (idx % 4) * (meta.ticks_per_quarter // 8)
        out.append(MidiNote(note.pitch, note.velocity, (note.start_tick + offset) % meta.loop_ticks, dur))
    return sanitize_notes(out, meta)


def _melodic_mutation(notes: list[MidiNote], meta: LoopMeta) -> list[MidiNote]:
    steps = [0, 2, -2, 5, -5, 7]
    out = [
        MidiNote(
            pitch=clamp_pitch(note.pitch + steps[idx % len(steps)]),
            velocity=note.velocity,
            start_tick=note.start_tick,
            duration_tick=note.duration_tick,
        )
        for idx, note in enumerate(notes)
    ]
    return sanitize_notes(out, meta)


def _reharmonized(notes: list[MidiNote], meta: LoopMeta) -> list[MidiNote]:
    out: list[MidiNote] = []
    for idx, note in enumerate(notes):
        chord_tone_shift = [0, 4, 7, 10][idx % 4]
        out.append(
            MidiNote(
                pitch=clamp_pitch((note.pitch // 12) * 12 + chord_tone_shift + (12 if note.pitch > 72 else 48)),
                velocity=note.velocity,
                start_tick=note.start_tick,
                duration_tick=note.duration_tick,
            )
        )
    return sanitize_notes(out, meta)


def _call_response(notes: list[MidiNote], meta: LoopMeta) -> list[MidiNote]:
    midpoint = meta.loop_ticks // 2
    call = [note for note in notes if note.start_tick < midpoint]
    if not call:
        call = notes[: max(1, len(notes) // 2)]
    response: list[MidiNote] = []
    for note in call:
        mirrored_start = (note.start_tick + midpoint) % meta.loop_ticks
        response.append(
            MidiNote(
                pitch=clamp_pitch(note.pitch + 5),
                velocity=clamp_velocity(note.velocity - 8),
                start_tick=mirrored_start,
                duration_tick=max(60, int(note.duration_tick * 0.8)),
            )
        )
    return sanitize_notes(call + response, meta)


def _tension(notes: list[MidiNote], meta: LoopMeta) -> list[MidiNote]:
    out: list[MidiNote] = []
    for idx, note in enumerate(notes):
        upward = 1 + (idx % 3)
        out.append(
            MidiNote(
                pitch=clamp_pitch(note.pitch + upward),
                velocity=clamp_velocity(note.velocity + 10),
                start_tick=note.start_tick,
                duration_tick=max(60, int(note.duration_tick * 0.75)),
            )
        )
    return sanitize_notes(out, meta)


def _release(notes: list[MidiNote], meta: LoopMeta) -> list[MidiNote]:
    out: list[MidiNote] = []
    for idx, note in enumerate(notes):
        downward = 2 if idx % 2 == 0 else 5
        out.append(
            MidiNote(
                pitch=clamp_pitch(note.pitch - downward),
                velocity=clamp_velocity(note.velocity - 14),
                start_tick=note.start_tick,
                duration_tick=min(meta.ticks_per_quarter * 2, int(note.duration_tick * 1.3)),
            )
        )
    return sanitize_notes(out, meta)


def _texture_chop(notes: list[MidiNote], meta: LoopMeta) -> list[MidiNote]:
    out: list[MidiNote] = []
    for note in notes:
        piece = max(45, note.duration_tick // 3)
        for step in range(3):
            out.append(
                MidiNote(
                    pitch=note.pitch,
                    velocity=clamp_velocity(note.velocity - (step * 6)),
                    start_tick=(note.start_tick + step * piece) % meta.loop_ticks,
                    duration_tick=piece,
                )
            )
    return sanitize_notes(out, meta)


TRANSFORMERS: dict[str, Callable[[list[MidiNote], LoopMeta], list[MidiNote]]] = {
    "sparse": _sparse,
    "dense": _dense,
    "syncopated": _syncopated,
    "rhythmic_mutation": _rhythmic_mutation,
    "melodic_mutation": _melodic_mutation,
    "reharmonized": _reharmonized,
    "call_response": _call_response,
    "tension": _tension,
    "release": _release,
    "texture_chop": _texture_chop,
}


def apply_variation(seed_notes: list[MidiNote], meta: LoopMeta, variation_name: str) -> list[MidiNote]:
    if variation_name not in TRANSFORMERS:
        raise ValueError(f"Unsupported variation {variation_name}")
    clean_seed = sanitize_notes(seed_notes, meta)
    transformed = TRANSFORMERS[variation_name](clean_seed, meta)
    distinct = assert_distinct(clean_seed, transformed, variation_name)
    return sanitize_notes(distinct, meta)


def generate_variation_cycle(
    seed_notes: list[MidiNote],
    meta: LoopMeta,
    count: int,
) -> list[tuple[str, list[MidiNote]]]:
    if count <= 0:
        return []
    out: list[tuple[str, list[MidiNote]]] = []
    names = list(VALID_VARIATIONS)
    for idx in range(count):
        name = names[idx % len(names)]
        notes = apply_variation(seed_notes, meta, name)
        out.append((name, notes))
    return out
