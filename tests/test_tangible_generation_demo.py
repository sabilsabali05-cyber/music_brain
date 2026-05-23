from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest
from mido import MidiFile, MidiTrack

from features.tangible_generation.demo_schema import DemoCompositionPlan, DemoSection
from scripts.generate_tangible_demo import PHI, calculate_climax_seconds, generate_tangible_demo
from scripts.validate_tangible_demo import validate_tangible_demo


def _write_fake_generative_dataset(dataset_dir: Path) -> None:
    dataset_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    task_types = [
        "continuation",
        "phrase_continuation",
        "groove_continuation",
        "harmony_continuation",
        "call_response",
        "section_transition",
        "buildup_to_release",
    ]
    for idx, task in enumerate(task_types):
        rows.append(
            {
                "example_id": f"example_{task}_{idx}",
                "task_type": task,
                "split_recommendation": "train" if idx % 2 == 0 else "validation",
                "quality_score": {"final_score": 0.88 - idx * 0.03},
                "target_representation": {
                    "midi_events": [
                        {"start": 0.0, "end": 0.4, "note": 60 + idx, "velocity": 90},
                        {"start": 0.5, "end": 1.0, "note": 64 + idx, "velocity": 88},
                        {"start": 1.1, "end": 1.6, "note": 67 + idx, "velocity": 84},
                    ]
                },
            }
        )
    lines = "\n".join(json.dumps(row) for row in rows) + "\n"
    (dataset_dir / "generative_examples.jsonl").write_text(lines, encoding="utf-8")
    (dataset_dir / "generative_manifest.json").write_text(json.dumps({"performance_id": "fake_performance"}), encoding="utf-8")


def _write_fake_sample_records(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {"sample_id": "kick_01", "source_path": "C:/private/kick.wav", "asset_type_guess": "drum_one_shot", "needs_human_review": True},
        {"sample_id": "bass_01", "source_path": "C:/private/bass.wav", "asset_type_guess": "bass_one_shot", "needs_human_review": True},
        {"sample_id": "chord_01", "source_path": "C:/private/chord.wav", "asset_type_guess": "chord_stab", "needs_human_review": True},
        {"sample_id": "lead_01", "source_path": "C:/private/lead.wav", "asset_type_guess": "synth_one_shot", "needs_human_review": True},
        {"sample_id": "texture_01", "source_path": "C:/private/texture.wav", "asset_type_guess": "texture", "needs_human_review": True},
        {"sample_id": "fx_01", "source_path": "C:/private/fx.wav", "asset_type_guess": "fx", "needs_human_review": True},
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_demo_plan_schema_dataclass() -> None:
    plan = DemoCompositionPlan(
        plan_id="demo",
        duration_seconds=180.0,
        structure_ratio="golden_ratio",
        goal="climax",
        climax_seconds=111.2,
        sections=[DemoSection("intro", "intro", 0.0, 20.0, "establish")],
    )
    payload = asdict(plan)
    assert payload["plan_id"] == "demo"
    assert payload["sections"][0]["section_id"] == "intro"


def test_ratio_timing_places_climax_near_phi() -> None:
    climax = calculate_climax_seconds(180.0, "golden_ratio")
    assert climax == pytest.approx(180.0 / PHI, abs=0.01)


def test_generator_creates_demo_from_fake_examples(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "datasets" / "generative_training" / "fake_perf" / "run_1"
    output_dir = tmp_path / "outputs" / "tangible_generation_v1"
    _write_fake_generative_dataset(dataset_dir)
    result = generate_tangible_demo(datasets_root=tmp_path / "datasets" / "generative_training", output_root=output_dir)
    assert (output_dir / "generated_song.mid").exists()
    assert result["note_counts"]["song"] > 0
    report = json.loads((output_dir / "generation_report.json").read_text(encoding="utf-8"))
    assert report["prototype_generated_from_existing_examples"] is True
    assert report["not_model_trained"] is True


def test_validation_rejects_empty_midi(tmp_path: Path) -> None:
    output_dir = tmp_path / "outputs" / "tangible_generation_v1"
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in ["generated_song.mid", "generated_drums.mid", "generated_bass.mid", "generated_chords.mid", "generated_lead.mid", "generated_texture_motifs.mid"]:
        midi = MidiFile()
        midi.tracks.append(MidiTrack())
        midi.save(str(output_dir / name))
    for name in ["demo_composition_plan.json", "demo_composition_plan.md", "generation_report.md", "ableton_track_plan.json", "ableton_track_plan.md"]:
        (output_dir / name).write_text("{}", encoding="utf-8")
    (output_dir / "generation_report.json").write_text(
        json.dumps(
            {
                "prototype_generated_from_existing_examples": True,
                "not_model_trained": True,
                "not_ground_truth": True,
                "not_final_mix": True,
                "needs_human_review": True,
                "model_training_claim": False,
                "synplant_automation_claim": False,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        validate_tangible_demo(output_dir)


def test_missing_sample_index_does_not_fail_generation(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "datasets" / "generative_training" / "fake_perf" / "run_1"
    output_dir = tmp_path / "outputs" / "tangible_generation_v1"
    _write_fake_generative_dataset(dataset_dir)
    result = generate_tangible_demo(
        datasets_root=tmp_path / "datasets" / "generative_training",
        output_root=output_dir,
        sample_records_path=tmp_path / "does_not_exist.jsonl",
    )
    assert (output_dir / "generated_song.mid").exists()
    assert result["sample_suggestions_generated"] is False
    assert (output_dir / "synplant_seed_suggestions.md").exists()


def test_sound_suggestions_use_index_without_copying_audio(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "datasets" / "generative_training" / "fake_perf" / "run_1"
    output_dir = tmp_path / "outputs" / "tangible_generation_v1"
    _write_fake_generative_dataset(dataset_dir)
    sample_records = tmp_path / "datasets" / "sample_libraries" / "local_sounds_desktop" / "sample_seed_records.jsonl"
    _write_fake_sample_records(sample_records)
    result = generate_tangible_demo(
        datasets_root=tmp_path / "datasets" / "generative_training",
        output_root=output_dir,
        sample_records_path=sample_records,
    )
    assert result["sample_suggestions_generated"] is True
    assert (output_dir / "synplant_seed_suggestions.json").exists()
    copied_audio = [p for p in output_dir.rglob("*") if p.is_file() and p.suffix.lower() in {".wav", ".mp3", ".flac"}]
    assert copied_audio == []
