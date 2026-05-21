from __future__ import annotations

import json
from pathlib import Path

from mido import Message, MidiFile, MidiTrack

from scripts.stitch_midi import build_dry_run_lines, stitch_manifest
from scripts.validate_merged_midi import validate_merged_midi


def _write_simple_midi(path: Path, *, notes: list[int], pre_delay: int = 0) -> None:
    midi = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    midi.tracks.append(track)
    if pre_delay > 0:
        track.append(Message("note_on", note=notes[0], velocity=64, time=pre_delay))
        track.append(Message("note_off", note=notes[0], velocity=0, time=240))
        start_index = 1
    else:
        start_index = 0
    for note in notes[start_index:]:
        track.append(Message("note_on", note=note, velocity=64, time=0))
        track.append(Message("note_off", note=note, velocity=0, time=240))
    midi.save(path)


def test_stitch_midi_dry_run_reports_windows_and_warnings(tmp_path: Path) -> None:
    midi_file = tmp_path / "win0.mid"
    _write_simple_midi(midi_file, notes=[60])
    manifest = {
        "segmentation_run_id": "run_123",
        "duration_seconds": 120.0,
        "transcription_windows": [
            {
                "index": 0,
                "status": "success",
                "global_start_seconds": 0.0,
                "global_end_seconds": 35.0,
                "core_start_seconds": 0.0,
                "core_end_seconds": 30.0,
                "midi_path": midi_file.as_posix(),
            },
            {
                "index": 1,
                "status": "failed",
                "global_start_seconds": 25.0,
                "global_end_seconds": 70.0,
                "core_start_seconds": 30.0,
                "core_end_seconds": 65.0,
                "midi_path": None,
            },
        ],
    }
    manifest_path = tmp_path / "segments_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    lines = build_dry_run_lines(manifest_path)
    text = "\n".join(lines)
    assert "windows_total: 2" in text
    assert "windows_with_midi: 1" in text
    assert "windows_missing_or_failed: 1" in text
    assert "warning=context_overlap_present trim_to_core_required" in text
    assert "index=1 status=failed" in text


def test_stitch_manifest_writes_outputs_and_discards_context(tmp_path: Path) -> None:
    win0 = tmp_path / "win0.mid"
    win1 = tmp_path / "win1.mid"
    _write_simple_midi(win0, notes=[60, 62], pre_delay=480)  # first note starts in pre-context
    _write_simple_midi(win1, notes=[64, 65])
    manifest = {
        "segmentation_run_id": "run_merge",
        "segmentation_run_dir": (tmp_path / "run_merge").as_posix(),
        "duration_seconds": 40.0,
        "transcription_windows": [
            {
                "index": 0,
                "status": "success",
                "global_start_seconds": 0.0,
                "global_end_seconds": 12.0,
                "core_start_seconds": 1.0,
                "core_end_seconds": 10.0,
                "midi_path": win0.as_posix(),
            },
            {
                "index": 1,
                "status": "success",
                "global_start_seconds": 8.0,
                "global_end_seconds": 22.0,
                "core_start_seconds": 8.0,
                "core_end_seconds": 20.0,
                "midi_path": win1.as_posix(),
            },
            {
                "index": 2,
                "status": "failed",
                "global_start_seconds": 20.0,
                "global_end_seconds": 30.0,
                "core_start_seconds": 21.0,
                "core_end_seconds": 29.0,
                "midi_path": None,
            },
        ],
    }
    manifest_path = tmp_path / "segments_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    output_midi, report_path, report = stitch_manifest(manifest_path, allow_partial=True)
    assert output_midi.exists()
    assert report_path.exists()
    assert report["status"] == "success"
    assert report["windows_total"] == 3
    assert report["windows_used"] == 2
    assert report["windows_skipped"] == 1
    assert report["events_discarded_context"] > 0
    assert report["events_kept"] > 0
    assert report["note_on_count"] > 0
    assert report["partial_stitch"] is True
    assert report["warning"] == "partial stitch: merged MIDI does not represent full performance"
    assert report["skipped_window_ids"] == ["win_0002"]
    validation = validate_merged_midi(output_midi)
    assert validation["status"] == "success"


def test_stitch_manifest_requires_flag_for_partial_merges(tmp_path: Path) -> None:
    win0 = tmp_path / "win0.mid"
    _write_simple_midi(win0, notes=[60])
    manifest = {
        "segmentation_run_id": "run_partial_guard",
        "duration_seconds": 20.0,
        "transcription_windows": [
            {
                "window_id": "win_0000",
                "index": 0,
                "status": "success",
                "global_start_seconds": 0.0,
                "global_end_seconds": 8.0,
                "core_start_seconds": 0.0,
                "core_end_seconds": 8.0,
                "midi_path": win0.as_posix(),
            },
            {
                "window_id": "win_0001",
                "index": 1,
                "status": "pending",
                "global_start_seconds": 8.0,
                "global_end_seconds": 20.0,
                "core_start_seconds": 8.0,
                "core_end_seconds": 20.0,
                "midi_path": None,
            },
        ],
    }
    manifest_path = tmp_path / "segments_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    try:
        stitch_manifest(manifest_path)
    except RuntimeError as exc:
        assert "Manifest has pending or failed windows" in str(exc)
    else:
        raise AssertionError("Expected stitch_manifest to block partial merge without allow_partial.")


def test_stitch_manifest_marks_complete_merges_as_not_partial(tmp_path: Path) -> None:
    win0 = tmp_path / "win0.mid"
    win1 = tmp_path / "win1.mid"
    _write_simple_midi(win0, notes=[60])
    _write_simple_midi(win1, notes=[64])
    manifest = {
        "segmentation_run_id": "run_complete",
        "duration_seconds": 30.0,
        "transcription_windows": [
            {
                "window_id": "win_0000",
                "index": 0,
                "status": "success",
                "global_start_seconds": 0.0,
                "global_end_seconds": 15.0,
                "core_start_seconds": 0.0,
                "core_end_seconds": 15.0,
                "midi_path": win0.as_posix(),
            },
            {
                "window_id": "win_0001",
                "index": 1,
                "status": "success",
                "global_start_seconds": 15.0,
                "global_end_seconds": 30.0,
                "core_start_seconds": 15.0,
                "core_end_seconds": 30.0,
                "midi_path": win1.as_posix(),
            },
        ],
    }
    manifest_path = tmp_path / "segments_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    _, _, report = stitch_manifest(manifest_path)
    assert report["status"] == "success"
    assert report["partial_stitch"] is False
    assert report["warning"] is None
