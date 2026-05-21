from __future__ import annotations

import json
from pathlib import Path

from mido import Message, MidiFile, MidiTrack

from scripts.compare_segmentations import compare_segmentations


def _write_run(folder: Path, run_id: str, strategy_used: str, fallback_used: bool, status: str) -> Path:
    run_dir = folder / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    midi_path = run_dir / "out.mid"
    if status == "success":
        midi = MidiFile()
        t = MidiTrack()
        t.append(Message("note_on", note=60, velocity=64, time=0))
        t.append(Message("note_off", note=60, velocity=0, time=120))
        midi.tracks.append(t)
        midi.save(midi_path)

    manifest = {
        "segmentation_run_id": run_id,
        "strategy_requested": "energy",
        "strategy_used": strategy_used,
        "fallback_used": fallback_used,
        "musical_segments": [{}, {}],
        "segmentation_parameters": {
            "boundary_threshold": 0.55,
            "min_segment_seconds": 30.0,
            "max_segment_seconds": 90.0,
            "rms_weight": 0.2,
            "onset_weight": 0.3,
            "chroma_weight": 0.25,
            "timbre_weight": 0.25,
        },
        "segmentation_diagnostics": {
            "candidate_boundary_count": 3,
            "detected_boundary_count": 3,
            "accepted_boundary_count": 1,
            "available_features": ["rms", "onset_strength"],
            "missing_features": ["chroma_change"],
        },
        "transcription_windows": [
            {
                "status": status,
                "midi_path": midi_path.as_posix() if status == "success" else None,
            }
        ],
    }
    manifest_path = run_dir / "segments_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def test_compare_segmentations_summarizes_multiple_runs(tmp_path: Path) -> None:
    source_folder = tmp_path / "segments" / "piece"
    _write_run(source_folder, "20260101T000001_fixed_with_context", "fixed_with_context", True, "failed")
    _write_run(source_folder, "20260101T000002_energy_v1", "energy_v1", False, "success")

    rows = compare_segmentations(source_folder)
    assert len(rows) == 2
    energy_row = next(row for row in rows if row["strategy_used"] == "energy_v1")
    assert energy_row["successful_windows"] == 1
    assert energy_row["failed_windows"] == 0
    assert energy_row["total_note_on_count"] == 1
    assert energy_row["candidate_boundary_count"] == 3
    assert energy_row["available_features"] == "rms,onset_strength"
    assert energy_row["boundary_threshold"] == 0.55
    assert energy_row["min_segment_seconds"] == 30.0


def test_compare_segmentations_includes_legacy_and_run_folders(tmp_path: Path) -> None:
    source_folder = tmp_path / "segments" / "piece"
    source_folder.mkdir(parents=True, exist_ok=True)
    legacy_manifest = {
        "segmentation_strategy": "fixed_with_context",
        "musical_segments": [],
        "transcription_windows": [],
        "segmentation_diagnostics": {},
    }
    (source_folder / "segments_manifest.json").write_text(json.dumps(legacy_manifest), encoding="utf-8")
    _write_run(source_folder, "20260101T000002_energy_v1", "energy_v1", False, "success")

    rows = compare_segmentations(source_folder)
    assert len(rows) == 2
