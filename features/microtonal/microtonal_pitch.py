from __future__ import annotations


def midi_note_to_frequency(note: float, *, a4_frequency: float = 440.0) -> float:
    return a4_frequency * (2.0 ** ((float(note) - 69.0) / 12.0))
