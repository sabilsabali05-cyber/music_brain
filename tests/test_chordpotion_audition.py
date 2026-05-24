from __future__ import annotations

from pathlib import Path

from mido import Message, MidiFile, MidiTrack

from features.local_rendering.chordpotion_audition import run_chordpotion_audition
from features.local_rendering.chordpotion_intent_schema import ChordPotionTargetIntent, ChordPotionTargetPatternFamily
from features.local_rendering.chordpotion_preset_registry import ChordPotionPresetProfile


def _write_simple_midi(path: Path) -> None:
    midi = MidiFile()
    track = MidiTrack()
    midi.tracks.append(track)
    track.append(Message("note_on", note=60, velocity=80, time=10))
    track.append(Message("note_off", note=60, velocity=0, time=40))
    midi.save(str(path))


def test_audition_honestly_blocks_without_capture_or_render(tmp_path: Path) -> None:
    harmony = tmp_path / "h.mid"
    _write_simple_midi(harmony)
    intent = ChordPotionTargetIntent(
        "i",
        "g",
        "chord_pattern_generator",
        "h.mid",
        ChordPotionTargetPatternFamily.ROLLING_CHORD_MOTION,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        "mid",
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        "musical",
        "warm",
        "functional",
        0.6,
    )
    presets = [ChordPotionPresetProfile("p1", "Preset1", "Preset1", "cat", "rolling_chord_motion", 0.5, 0.5, 0.5, "mid", "warm")]
    result = run_chordpotion_audition(tmp_path, harmony, intent, presets, audition_id="aud1")
    assert result.blocked_by_local_config is True
    assert result.blocker == "blocked_by_local_config"
    assert result.candidate_results[0].transformed_midi_captured is False
