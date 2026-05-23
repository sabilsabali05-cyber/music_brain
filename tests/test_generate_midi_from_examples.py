from __future__ import annotations

import json
from pathlib import Path

from mido import Message, MidiFile, MidiTrack

from scripts.generate_midi_from_examples import generate_midi_from_examples
from scripts.validate_generated_midi_outputs import validate_generated_midi_outputs


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(json.dumps(row) for row in rows)
    path.write_text((body + "\n") if body else "", encoding="utf-8")


def _note_on_count(midi_path: Path) -> int:
    midi = MidiFile(str(midi_path))
    return sum(
        1
        for track in midi.tracks
        for msg in track
        if getattr(msg, "type", "") == "note_on" and int(getattr(msg, "velocity", 0)) > 0
    )


def _extract_notes_with_times(midi_path: Path) -> list[tuple[int, int, int]]:
    midi = MidiFile(str(midi_path))
    timeline = 0
    out: list[tuple[int, int, int]] = []
    for msg in midi.tracks[0]:
        timeline += int(getattr(msg, "time", 0))
        if getattr(msg, "type", "") == "note_on" and int(getattr(msg, "velocity", 0)) > 0:
            out.append((timeline, int(msg.note), int(msg.velocity)))
    return out


def _write_reference_midi(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    midi = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    midi.tracks.append(track)
    track.append(Message("note_on", note=60, velocity=90, time=120))
    track.append(Message("note_off", note=60, velocity=0, time=120))
    track.append(Message("note_on", note=62, velocity=70, time=120))
    track.append(Message("note_off", note=62, velocity=0, time=120))
    midi.save(path.as_posix())


def _seed_generative_dataset(tmp_path: Path) -> Path:
    performance_id = "perf_gen"
    run_id = "run_1"
    dataset_dir = tmp_path / "datasets" / "generative_training" / performance_id / run_id
    ref_midi = tmp_path / "refs" / "target_ref.mid"
    _write_reference_midi(ref_midi)
    _write_json(
        dataset_dir / "generative_manifest.json",
        {
            "performance_id": performance_id,
            "segment_run_id": run_id,
            "generative_examples_count": 3,
            "split_counts": {"train": 2, "validation": 1, "review": 0, "exclude": 0},
            "examples_by_task_type": {"continuation": 3},
            "average_quality_score": 0.76,
            "examples_per_minute": 1.0,
            "high_quality_examples_per_minute": 0.5,
        },
    )
    _write_jsonl(
        dataset_dir / "generative_examples.jsonl",
        [
            {
                "example_id": "ex_high",
                "performance_id": performance_id,
                "segment_run_id": run_id,
                "task_type": "continuation",
                "split_recommendation": "train",
                "quality_score": {"final_score": 0.9},
                "context_start_seconds": 0.0,
                "context_end_seconds": 4.0,
                "target_start_seconds": 4.0,
                "target_end_seconds": 8.0,
                "target_representation": {
                    "midi_events": [
                        {"start": 4.0, "end": 4.3, "note": 60, "velocity": 90},
                        {"start": 4.4, "end": 4.7, "note": 62, "velocity": 80},
                        {"start": 4.8, "end": 5.1, "note": 64, "velocity": 70},
                        {"start": 5.2, "end": 5.5, "note": 65, "velocity": 60},
                    ]
                },
                "conditioning": {"tempo_context": {"local_tempo_bpm_median": 120.0}},
                "target_midi_ref": ref_midi.as_posix(),
                "context_midi_ref": ref_midi.as_posix(),
            },
            {
                "example_id": "ex_mid",
                "performance_id": performance_id,
                "segment_run_id": run_id,
                "task_type": "continuation",
                "split_recommendation": "validation",
                "quality_score": {"final_score": 0.7},
                "context_start_seconds": 0.0,
                "context_end_seconds": 2.0,
                "target_start_seconds": 2.0,
                "target_end_seconds": 4.0,
                "target_representation": {"midi_events": []},
                "conditioning": {"tempo_context": {"local_tempo_bpm_median": 100.0}},
                "target_midi_ref": ref_midi.as_posix(),
                "context_midi_ref": ref_midi.as_posix(),
            },
            {
                "example_id": "ex_low",
                "performance_id": performance_id,
                "segment_run_id": run_id,
                "task_type": "continuation",
                "split_recommendation": "train",
                "quality_score": {"final_score": 0.6},
                "context_start_seconds": 0.0,
                "context_end_seconds": 2.0,
                "target_start_seconds": 2.0,
                "target_end_seconds": 4.0,
                "target_representation": {
                    "midi_events": [
                        {"start": 2.0, "end": 2.2, "note": 55, "velocity": 50},
                        {"start": 2.25, "end": 2.5, "note": 57, "velocity": 45},
                    ]
                },
                "conditioning": {"tempo_context": {"local_tempo_bpm_median": 90.0}},
                "target_midi_ref": ref_midi.as_posix(),
                "context_midi_ref": ref_midi.as_posix(),
            },
        ],
    )
    return dataset_dir


def test_generator_creates_valid_midi_and_report_with_provenance(tmp_path: Path, monkeypatch) -> None:
    dataset_dir = _seed_generative_dataset(tmp_path)
    monkeypatch.chdir(tmp_path)
    output_dir, report_path, _ = generate_midi_from_examples(
        dataset_dir,
        task="continuation",
        split="train",
        count=1,
        mode="direct_target",
        transpose_semitones=2,
        density_nth=2,
        density_velocity_threshold=1,
        normalize_start=True,
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert output_dir.exists()
    assert report["selection"]["count_generated"] == 1
    assert report["generated_examples"][0]["example_id"] == "ex_high"
    assert report["generated_examples"][0]["provenance"]["prototype_generated_from_existing_examples"] is True
    assert report["generated_examples"][0]["provenance"]["model_trained_output"] is False
    midi_path = Path(report["generated_examples"][0]["output_midi_path"])
    assert midi_path.exists()
    assert _note_on_count(midi_path) > 0
    validation = validate_generated_midi_outputs(output_dir)
    assert validation["status"] == "success"


def test_transpose_mode_preserves_timing_and_changes_pitch(tmp_path: Path, monkeypatch) -> None:
    dataset_dir = _seed_generative_dataset(tmp_path)
    monkeypatch.chdir(tmp_path)
    output_dir, report_path, _ = generate_midi_from_examples(
        dataset_dir,
        task="continuation",
        split="train",
        count=1,
        mode="transpose",
        transpose_semitones=2,
        density_nth=2,
        density_velocity_threshold=1,
        normalize_start=True,
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    midi_path = Path(report["generated_examples"][0]["output_midi_path"])
    transformed = _extract_notes_with_times(midi_path)
    assert transformed
    assert [item[1] for item in transformed] == [62, 64, 66, 67]
    assert [item[0] for item in transformed] == [0, 384, 768, 1152]
    assert validate_generated_midi_outputs(output_dir)["status"] == "success"


def test_density_slice_reduces_note_count(tmp_path: Path, monkeypatch) -> None:
    dataset_dir = _seed_generative_dataset(tmp_path)
    monkeypatch.chdir(tmp_path)
    output_dir, report_path, _ = generate_midi_from_examples(
        dataset_dir,
        task="continuation",
        split="train",
        count=1,
        mode="density_slice",
        transpose_semitones=2,
        density_nth=2,
        density_velocity_threshold=1,
        normalize_start=True,
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    midi_path = Path(report["generated_examples"][0]["output_midi_path"])
    assert _note_on_count(midi_path) == 2
    assert validate_generated_midi_outputs(output_dir)["status"] == "success"


def test_validator_rejects_empty_midi(tmp_path: Path) -> None:
    output_dir = tmp_path / "outputs" / "generated_midi" / "perf" / "run"
    output_dir.mkdir(parents=True, exist_ok=True)
    empty_midi = output_dir / "generated_continuation_1.mid"
    midi = MidiFile(ticks_per_beat=480)
    midi.tracks.append(MidiTrack())
    midi.save(empty_midi.as_posix())
    _write_json(
        output_dir / "generation_report.json",
        {
            "provenance_notice": {
                "prototype_generated_from_existing_examples": True,
                "not_original_model_composition": True,
                "not_ground_truth": True,
                "model_trained_output": False,
            },
            "generated_examples": [
                {
                    "example_id": "ex1",
                    "task_type": "continuation",
                    "split_recommendation": "train",
                    "quality_score": 0.9,
                    "output_midi_path": empty_midi.as_posix(),
                    "provenance": {
                        "prototype_generated_from_existing_examples": True,
                        "not_ground_truth": True,
                        "model_trained_output": False,
                        "weak_labels_promoted_to_ground_truth": False,
                    },
                }
            ],
        },
    )
    (output_dir / "generation_summary.md").write_text("# test\n", encoding="utf-8")
    result = validate_generated_midi_outputs(output_dir)
    assert result["status"] == "failed"
    assert any("zero note_on events" in error for error in result["errors"])
