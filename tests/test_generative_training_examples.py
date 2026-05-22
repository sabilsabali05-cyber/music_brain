from __future__ import annotations

import json
from pathlib import Path

from mido import Message, MidiFile, MidiTrack

from scripts.build_generative_training_examples import build_generative_training_examples
from scripts.validate_generative_training_examples import validate_generative_training_examples


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_midi(path: Path, notes: list[int]) -> None:
    midi = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    midi.tracks.append(track)
    for idx, note in enumerate(notes):
        track.append(Message("note_on", note=note, velocity=80 + (idx % 20), time=4800))
        track.append(Message("note_off", note=note, velocity=0, time=2400))
    path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(path.as_posix())


def _setup_workspace(tmp_path: Path) -> tuple[Path, str, str]:
    performance_id = "perf_gen"
    run_id = "run_gen_1"
    audio = tmp_path / "audio" / "src.wav"
    audio.parent.mkdir(parents=True, exist_ok=True)
    audio.write_bytes(b"RIFFfake")
    merged = tmp_path / "samples" / "segments" / performance_id / run_id / "merged" / "merged_performance.mid"
    _write_midi(merged, [48, 50, 52, 53, 55, 57, 59, 60] * 80)
    windows_dir = tmp_path / "samples" / "segments" / performance_id / run_id / "windows"
    w0 = windows_dir / "w0.mid"
    w1 = windows_dir / "w1.mid"
    w2 = windows_dir / "w2.mid"
    w3 = windows_dir / "w3.mid"
    _write_midi(w0, [48, 50, 52, 53, 55, 57, 59, 60])
    _write_midi(w1, [60, 62, 64, 65, 67, 69, 71, 72, 74])
    _write_midi(w2, [72, 74, 76, 77, 79, 81, 83, 84])
    _write_midi(w3, [36, 36, 38, 40, 41, 43, 45, 47])

    segments_manifest = tmp_path / "samples" / "segments" / performance_id / run_id / "segments_manifest.json"
    _write_json(
        segments_manifest,
        {
            "duration_seconds": 40.0,
            "musical_segments": [
                {"segment_id": "s0", "index": 0, "global_start_seconds": 0.0, "global_end_seconds": 10.0, "section_label": "intro"},
                {"segment_id": "s1", "index": 1, "global_start_seconds": 10.0, "global_end_seconds": 20.0, "section_label": "verse"},
                {"segment_id": "s2", "index": 2, "global_start_seconds": 20.0, "global_end_seconds": 30.0, "section_label": "hook"},
                {"segment_id": "s3", "index": 3, "global_start_seconds": 30.0, "global_end_seconds": 40.0, "section_label": "outro"},
            ],
            "transcription_windows": [
                {"window_id": "w0", "index": 0, "core_start_seconds": 0.0, "core_end_seconds": 10.0, "midi_path": w0.resolve().as_posix(), "status": "success"},
                {"window_id": "w1", "index": 1, "core_start_seconds": 10.0, "core_end_seconds": 20.0, "midi_path": w1.resolve().as_posix(), "status": "success"},
                {"window_id": "w2", "index": 2, "core_start_seconds": 20.0, "core_end_seconds": 30.0, "midi_path": w2.resolve().as_posix(), "status": "success"},
                {"window_id": "w3", "index": 3, "core_start_seconds": 30.0, "core_end_seconds": 40.0, "midi_path": w3.resolve().as_posix(), "status": "success"},
            ],
        },
    )
    perf_manifest = tmp_path / "performances" / "library" / performance_id / "performance_manifest.json"
    _write_json(
        perf_manifest,
        {
            "performance_id": performance_id,
            "source_name": "src.wav",
            "source_path": audio.resolve().as_posix(),
            "active_segments_manifest_path": segments_manifest.resolve().as_posix(),
            "active_merged_midi_path": merged.resolve().as_posix(),
        },
    )
    feature_dir = tmp_path / "features" / "performances" / performance_id / run_id
    _write_json(feature_dir / "feature_pack_manifest.json", {"performance_id": performance_id, "segment_run_id": run_id})
    _write_json(feature_dir / "rhythm_features.json", {"records": [], "rhythm_motifs": {"motifs": []}, "rhythm_motif_groups": [{"motif_group_id": "mg1", "region_ids": ["route_w1", "route_w2"], "rhythm_family_confidence": 0.7}]})
    _write_json(feature_dir / "harmony_features.json", {"records": [], "chord_movement_summary": {}})
    _write_json(feature_dir / "rhythm_time" / "meter_time_features.json", {"confidence": 0.7, "ambiguity": 0.3, "summary": {"subdivision_histogram": {"straight_eighths": 3}, "macro_section_candidates": ["intro", "verse"]}, "beat_meter_hypotheses": [{"meter": "4/4", "confidence": 0.7, "ambiguity": 0.3}]})
    _write_json(
        feature_dir / "pitch_harmony" / "pitch_harmony_features.json",
        {
            "summary": {},
            "macro_record": {"key_hypotheses": [{"key": "C", "confidence": 0.7}], "register_density_arc": {}},
            "interval_analysis": [{"x": 1}],
            "melody_contour": [{"x": 1}],
            "harmony_sonority": [{"ambiguity": 0.2}],
            "chord_movement": [{"x": 1}],
            "counterpoint": [{"x": 1}],
            "tuning_system": [{"microtonal_analysis_available": False}],
        },
    )
    _write_json(feature_dir / "tags.json", {"top_unique_tags": [{"tag": "gospel_choir"}, {"tag": "dense_activity"}]})
    _write_json(
        feature_dir / "routing" / "content_region_routes.json",
        {
            "routes": [
                {"route_id": "route_w0", "source_record_id": "route_w0", "start_seconds": 0.0, "end_seconds": 10.0, "content_state": "rhythm_dominant", "confidence": 0.8},
                {"route_id": "route_w1", "source_record_id": "route_w1", "start_seconds": 10.0, "end_seconds": 20.0, "content_state": "rhythm_dominant", "confidence": 0.8},
                {"route_id": "route_w2", "source_record_id": "route_w2", "start_seconds": 20.0, "end_seconds": 30.0, "content_state": "polyphonic_full_mix", "confidence": 0.85},
                {"route_id": "route_w3", "source_record_id": "route_w3", "start_seconds": 30.0, "end_seconds": 40.0, "content_state": "silence_or_noise", "confidence": 0.95},
            ]
        },
    )
    _write_json(feature_dir / "routing" / "analysis_routing_decisions.json", {"decisions": []})
    _write_json(
        feature_dir / "trust" / "transcription_reliability.json",
        {
            "windows": [
                {"window_id": "w0", "transcription_reliability_score": 0.9},
                {"window_id": "w1", "transcription_reliability_score": 0.85},
                {"window_id": "w2", "transcription_reliability_score": 0.4},
                {"window_id": "w3", "transcription_reliability_score": 0.3},
            ]
        },
    )
    _write_json(feature_dir / "trust" / "quality_gates.json", {"overall_quality_status": "review_required"})
    ext = feature_dir / "external_model_features"
    _write_json(ext / "essentia_features.json", {"status": "success"})
    _write_json(ext / "music21_features.json", {"status": "success"})
    _write_json(ext / "model_consensus.json", {"consensus_status": "conflicted", "disagreements": ["tonal conflict"], "unresolved_conflicts": ["tonal_center_conflict"]})
    _write_json(ext / "model_witness_comparison.json", {"provider_status": {"essentia": "success", "music21": "success"}})
    return perf_manifest, performance_id, run_id


def test_builder_creates_continuation_infill_and_domain_tasks(tmp_path: Path, monkeypatch) -> None:
    manifest, performance_id, run_id = _setup_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    jsonl_path, manifest_path, _ = build_generative_training_examples(manifest)
    assert jsonl_path.exists()
    assert manifest_path.exists()
    rows = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    tasks = {row["task_type"] for row in rows}
    assert "continuation" in tasks
    assert "infill_missing_region" in tasks
    assert "groove_continuation" in tasks
    assert "harmony_continuation" in tasks
    assert "melody_continuation" in tasks
    infill = next(row for row in rows if row["task_type"] == "infill_missing_region")
    assert infill["context_start_seconds"] <= infill["target_start_seconds"] <= infill["target_end_seconds"] <= infill["context_end_seconds"]
    # silence_or_noise should not produce train split examples
    silence_rows = [row for row in rows if row["conditioning"]["content_state"] == "silence_or_noise"]
    assert silence_rows == []
    # weak style tags are conditioning-only
    assert "style_tags_weak" in rows[0]["conditioning"]
    assert "style_tags_ground_truth" not in rows[0]["conditioning"]
    out_dir = tmp_path / "datasets" / "generative_training" / performance_id / run_id
    assert out_dir.exists()


def test_quality_score_penalizes_low_reliability(tmp_path: Path, monkeypatch) -> None:
    manifest, _, _ = _setup_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    jsonl_path, _, _ = build_generative_training_examples(manifest)
    rows = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_target = {f"{row['target_start_seconds']}-{row['target_end_seconds']}": row for row in rows if row["task_type"] == "continuation"}
    high = by_target["10.0-20.0"]["quality_score"]["final_score"]
    low = by_target["30.0-40.0"]["quality_score"]["final_score"] if "30.0-40.0" in by_target else 0.0
    assert high > low


def test_validator_rejects_missing_refs_and_huge_arrays(tmp_path: Path, monkeypatch) -> None:
    manifest, performance_id, run_id = _setup_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    jsonl_path, _, _ = build_generative_training_examples(manifest)
    rows = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows[0]["target_midi_ref"] = None
    rows[0]["target_representation"]["pitch_tokens"] = [f"n{x}" for x in range(400)]
    rows[0]["split_recommendation"] = "bad_split"
    jsonl_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    dataset_dir = tmp_path / "datasets" / "generative_training" / performance_id / run_id
    result = validate_generative_training_examples(dataset_dir)
    assert result["status"] == "failed"
    assert any("target_midi_ref" in err for err in result["errors"])
    assert any("huge embedded arrays" in err for err in result["errors"])
    assert any("invalid split_recommendation" in err for err in result["errors"])

