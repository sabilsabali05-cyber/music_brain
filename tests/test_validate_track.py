import json
from pathlib import Path

from mido import Message, MidiFile, MidiTrack

from scripts.validate_track import validate_track


def _write_fake_track(tmp_path: Path) -> Path:
    track_folder = tmp_path / "library" / "trk_test"
    (track_folder / "analysis").mkdir(parents=True)
    (track_folder / "original").mkdir(parents=True)
    (track_folder / "midi").mkdir(parents=True)

    report = {
        "status": "success",
        "provider_used": "yourmt3",
        "backend": "modal",
        "fallback_used": False,
    }
    (track_folder / "analysis" / "job_report.json").write_text(json.dumps(report), encoding="utf-8")
    (track_folder / "original" / "normalized.wav").write_bytes(b"RIFFfake")

    midi = MidiFile()
    midi_track = MidiTrack()
    midi_track.append(Message("program_change", program=0, time=0))
    midi_track.append(Message("note_on", note=60, velocity=64, time=0))
    midi_track.append(Message("note_off", note=60, velocity=0, time=120))
    midi.tracks.append(midi_track)
    midi.save(track_folder / "midi" / "full_mix.mid")
    return track_folder


def test_validate_track_success(tmp_path: Path) -> None:
    track_folder = _write_fake_track(tmp_path)

    ok, messages = validate_track(track_folder)

    assert ok is True
    assert any("MIDI parse ok" in msg for msg in messages)


def test_validate_track_failure_when_report_fields_wrong(tmp_path: Path) -> None:
    track_folder = _write_fake_track(tmp_path)
    bad_report = {
        "status": "failed",
        "provider_used": "none",
        "backend": "modal",
        "fallback_used": True,
    }
    (track_folder / "analysis" / "job_report.json").write_text(json.dumps(bad_report), encoding="utf-8")

    ok, messages = validate_track(track_folder)

    assert ok is False
    assert any("Expected status=success" in msg for msg in messages)
    assert any("Expected provider_used=yourmt3" in msg for msg in messages)
    assert any("Expected fallback_used=false" in msg for msg in messages)
