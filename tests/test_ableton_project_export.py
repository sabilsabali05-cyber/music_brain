from __future__ import annotations

import json
from pathlib import Path

import pytest
from mido import Message, MidiFile, MidiTrack

from scripts.export_ableton_project_v1 import export_ableton_project_v1
from scripts.validate_ableton_project_export import validate_ableton_project_export


def _write_midi(path: Path, note: int = 60) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    midi = MidiFile()
    track = MidiTrack()
    midi.tracks.append(track)
    track.append(Message("note_on", note=note, velocity=90, time=0))
    track.append(Message("note_off", note=note, velocity=0, time=120))
    midi.save(str(path))


def _make_tangible_folder(base: Path) -> Path:
    folder = base / "outputs" / "tangible_generation_v1"
    for idx, name in enumerate(
        [
            "generated_song.mid",
            "generated_drums.mid",
            "generated_bass.mid",
            "generated_chords.mid",
            "generated_lead.mid",
            "generated_texture_motifs.mid",
        ]
    ):
        _write_midi(folder / name, note=60 + idx)
    (folder / "demo_composition_plan.json").write_text(
        json.dumps(
            {
                "sections": [{"section_id": "intro", "start_seconds": 0.0, "end_seconds": 22.0}],
            }
        ),
        encoding="utf-8",
    )
    (folder / "generation_report.json").write_text(
        json.dumps({"ratio_timing": {"duration_seconds": 180.0}}),
        encoding="utf-8",
    )
    (folder / "synplant_seed_suggestions.json").write_text(
        json.dumps(
            [
                {
                    "track_role": "drums",
                    "sample_id": "seed_drum_01",
                    "source_path": "C:/Users/example/OneDrive/sounds/kick.wav",
                    "asset_type_guess": "drum_one_shot",
                }
            ]
        ),
        encoding="utf-8",
    )
    return folder


def test_export_creates_ableton_project_folder_and_midi(tmp_path: Path) -> None:
    tangible = _make_tangible_folder(tmp_path)
    export_root = tmp_path / "outputs" / "ableton_project_v1" / "AI_Generated_Song_Project"
    result = export_ableton_project_v1(tangible, export_project_path=export_root)
    assert export_root.exists()
    assert len(result["midi_files_copied"]) >= 6
    assert (export_root / "track_setup.json").exists()
    assert (export_root / "README_FIRST.md").exists()


def test_public_summary_does_not_contain_private_paths(tmp_path: Path) -> None:
    tangible = _make_tangible_folder(tmp_path)
    export_root = tmp_path / "outputs" / "ableton_project_v1" / "AI_Generated_Song_Project"
    export_ableton_project_v1(tangible, export_project_path=export_root)
    public_summary = (export_root / "synplant_seed_summary.md").read_text(encoding="utf-8")
    assert "C:/Users" not in public_summary
    assert "C:\\Users" not in public_summary


def test_private_seed_files_gitignored_rule_exists() -> None:
    gitignore = Path(".gitignore").read_text(encoding="utf-8")
    assert "outputs/ableton_project_v1/**/private_synplant_*_paths.json" in gitignore
    assert "outputs/ableton_project_v1/**/private_synplant_*_paths.md" in gitignore


def test_no_als_claim_and_copy_local_samples_default_false(tmp_path: Path) -> None:
    tangible = _make_tangible_folder(tmp_path)
    export_root = tmp_path / "outputs" / "ableton_project_v1" / "AI_Generated_Song_Project"
    export_ableton_project_v1(tangible, export_project_path=export_root)
    report = json.loads((export_root / "export_report.json").read_text(encoding="utf-8"))
    assert report["als_generation_status"] == "not_implemented_experimental_future"
    assert report["copy_local_samples_enabled"] is False
    assert not (export_root / "Samples").exists()


def test_validation_fails_if_public_files_contain_private_paths(tmp_path: Path) -> None:
    tangible = _make_tangible_folder(tmp_path)
    export_root = tmp_path / "outputs" / "ableton_project_v1" / "AI_Generated_Song_Project"
    export_ableton_project_v1(tangible, export_project_path=export_root)
    summary = export_root / "synplant_seed_summary.md"
    summary.write_text(summary.read_text(encoding="utf-8") + "\nC:\\Users\\private\\path.wav\n", encoding="utf-8")
    with pytest.raises(ValueError):
        validate_ableton_project_export(export_root)
