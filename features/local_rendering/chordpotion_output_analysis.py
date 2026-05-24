from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from mido import MidiFile


@dataclass
class ChordPotionOutputAnalysis:
    note_count: int
    note_density: float
    onset_density: float
    rhythmic_cells: int
    repeated_pattern_strength: float
    syncopation_score: float
    groove_stability: float
    chord_tone_preservation: float
    non_chord_tone_rate: float
    bass_interference: float
    top_voice_interference: float
    register_spread: float
    middle_register_mud: float
    velocity_shape: float
    pattern_repetition: float
    pattern_variation: float
    silence_breathing_space: float
    random_keyboard_penalty: float
    overbusy_penalty: float
    musical_motion_score: float
    emotional_support_score: float

    def as_dict(self) -> dict:
        return asdict(self)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def analyze_transformed_midi(midi_path: Path) -> ChordPotionOutputAnalysis:
    if not midi_path.exists():
        return ChordPotionOutputAnalysis(
            note_count=0,
            note_density=0.0,
            onset_density=0.0,
            rhythmic_cells=0,
            repeated_pattern_strength=0.0,
            syncopation_score=0.0,
            groove_stability=0.0,
            chord_tone_preservation=0.0,
            non_chord_tone_rate=1.0,
            bass_interference=0.0,
            top_voice_interference=0.0,
            register_spread=0.0,
            middle_register_mud=0.0,
            velocity_shape=0.0,
            pattern_repetition=0.0,
            pattern_variation=0.0,
            silence_breathing_space=1.0,
            random_keyboard_penalty=1.0,
            overbusy_penalty=1.0,
            musical_motion_score=0.0,
            emotional_support_score=0.0,
        )

    midi = MidiFile(str(midi_path))
    notes: list[int] = []
    velocities: list[int] = []
    onsets: list[float] = []
    current_time = 0.0
    for track in midi.tracks:
        current_time = 0.0
        for msg in track:
            current_time += msg.time
            if msg.type == "note_on" and msg.velocity > 0:
                notes.append(msg.note)
                velocities.append(msg.velocity)
                onsets.append(current_time)
    if not notes:
        return analyze_transformed_midi(Path("missing.mid"))

    note_count = len(notes)
    total_ticks = max(onsets) if onsets else float(note_count)
    normalized_duration = max(1.0, total_ticks / float(midi.ticks_per_beat))
    note_density = _clamp(note_count / (normalized_duration * 8.0))
    onset_density = _clamp(len(set(int(x) for x in onsets)) / max(1.0, normalized_duration * 6.0))
    rhythmic_cells = min(16, max(1, len(set(int(x * 2) for x in onsets))))
    repetition = _clamp(1.0 - (rhythmic_cells / 16.0))
    variation = _clamp(rhythmic_cells / 16.0)
    mean_note = sum(notes) / float(note_count)
    register_spread = _clamp((max(notes) - min(notes)) / 36.0)
    middle_band = sum(1 for n in notes if 52 <= n <= 72) / float(note_count)
    middle_register_mud = _clamp((middle_band - 0.5) * 2.0)
    low_ratio = sum(1 for n in notes if n < 48) / float(note_count)
    high_ratio = sum(1 for n in notes if n > 80) / float(note_count)
    bass_interference = _clamp(low_ratio * 1.5)
    top_voice_interference = _clamp(high_ratio * 1.5)
    velocity_span = max(velocities) - min(velocities) if velocities else 0
    velocity_shape = _clamp(velocity_span / 64.0)
    syncopation_score = _clamp(sum(1 for x in onsets if int(x) % 2 == 1) / float(note_count))
    groove_stability = _clamp(1.0 - abs(syncopation_score - 0.35))
    silence_breathing_space = _clamp(1.0 - note_density)
    random_keyboard_penalty = _clamp((variation * 0.6) if note_density > 0.75 else variation * 0.2)
    overbusy_penalty = _clamp((note_density - 0.55) * 2.2 if note_density > 0.55 else 0.0)
    motion = _clamp(register_spread * 0.6 + variation * 0.4)
    emotional_support = _clamp((1.0 - overbusy_penalty) * 0.5 + (1.0 - random_keyboard_penalty) * 0.5)
    chord_tone_preservation = _clamp(1.0 - non_chord_tone_proxy(mean_note, variation))
    non_chord_tone_rate = _clamp(1.0 - chord_tone_preservation)
    return ChordPotionOutputAnalysis(
        note_count=note_count,
        note_density=note_density,
        onset_density=onset_density,
        rhythmic_cells=rhythmic_cells,
        repeated_pattern_strength=repetition,
        syncopation_score=syncopation_score,
        groove_stability=groove_stability,
        chord_tone_preservation=chord_tone_preservation,
        non_chord_tone_rate=non_chord_tone_rate,
        bass_interference=bass_interference,
        top_voice_interference=top_voice_interference,
        register_spread=register_spread,
        middle_register_mud=middle_register_mud,
        velocity_shape=velocity_shape,
        pattern_repetition=repetition,
        pattern_variation=variation,
        silence_breathing_space=silence_breathing_space,
        random_keyboard_penalty=random_keyboard_penalty,
        overbusy_penalty=overbusy_penalty,
        musical_motion_score=motion,
        emotional_support_score=emotional_support,
    )


def non_chord_tone_proxy(mean_note: float, variation: float) -> float:
    return _clamp(abs((mean_note % 12) - 7.0) / 12.0 + variation * 0.2)
