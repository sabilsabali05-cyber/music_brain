from __future__ import annotations

import json
from pathlib import Path

from mido import Message, MidiFile, MidiTrack

from scripts.compute_transcription_reliability import compute_transcription_reliability
from scripts.evaluate_training_quality_gates import evaluate_training_quality_gates
from scripts.export_training_dataset_splits import export_training_dataset_splits
from scripts.extract_meter_time_features import extract_meter_time_features, infer_subdivision_type
from scripts.feature_dataset_common import compact_artifact_performance_dir
from scripts.validate_meter_time_features import validate_meter_time_features


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_midi(path: Path, notes: list[int], spacing_ticks: int = 120) -> None:
    midi = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    midi.tracks.append(track)
    for note in notes:
        track.append(Message("note_on", note=note, velocity=80, time=spacing_ticks))
        track.append(Message("note_off", note=note, velocity=0, time=120))
    path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(path)


def _setup_workspace(tmp_path: Path, *, performance_id: str = "perf_meter") -> tuple[Path, Path]:
    source_audio = tmp_path / "audio" / "source.wav"
    source_audio.parent.mkdir(parents=True, exist_ok=True)
    source_audio.write_bytes(b"RIFFfake")

    run_dir = tmp_path / "samples" / "segments" / "src" / "run_meter"
    midi_a = run_dir / "windows" / "win_0.mid"
    midi_b = run_dir / "windows" / "win_1.mid"
    _write_midi(midi_a, [60, 64, 67, 72, 74, 76, 79, 81], spacing_ticks=90)
    _write_midi(midi_b, [62, 65, 69, 74, 76, 77, 81, 84], spacing_ticks=120)
    merged = run_dir / "merged" / "merged_performance.mid"
    _write_midi(merged, [60, 64, 67, 72, 74, 76, 79, 81, 83, 84, 86, 88], spacing_ticks=100)
    segments_manifest = run_dir / "segments_manifest.json"
    _write_json(
        segments_manifest,
        {
            "duration_seconds": 40.0,
            "musical_segments": [
                {"segment_id": "seg_0", "global_start_seconds": 0.0, "global_end_seconds": 20.0},
                {"segment_id": "seg_1", "global_start_seconds": 20.0, "global_end_seconds": 40.0},
            ],
            "transcription_windows": [
                {
                    "window_id": "win_0",
                    "status": "success",
                    "core_start_seconds": 0.0,
                    "core_end_seconds": 20.0,
                    "midi_path": midi_a.resolve().as_posix(),
                },
                {
                    "window_id": "win_1",
                    "status": "success",
                    "core_start_seconds": 20.0,
                    "core_end_seconds": 40.0,
                    "midi_path": midi_b.resolve().as_posix(),
                },
            ],
        },
    )
    manifest = tmp_path / "performances" / "library" / performance_id / "performance_manifest.json"
    _write_json(
        manifest,
        {
            "performance_id": performance_id,
            "source_name": "source.wav",
            "source_path": source_audio.resolve().as_posix(),
            "duration_seconds": 40.0,
            "active_segments_manifest_path": segments_manifest.resolve().as_posix(),
            "active_analysis_path": None,
            "active_merged_midi_path": merged.resolve().as_posix(),
        },
    )
    feature_dir = tmp_path / "features" / "performances" / compact_artifact_performance_dir(performance_id) / "run_meter"
    _write_json(feature_dir / "rhythm_features.json", {"summary": {}, "records": []})
    _write_json(feature_dir / "harmony_features.json", {"summary": {}, "records": []})
    _write_json(feature_dir / "tags.json", {"tags": []})
    (feature_dir / "ai_training_records.jsonl").write_text(
        json.dumps(
            {
                "record_id": "r_meter_0",
                "performance_id": performance_id,
                "segment_run_id": "run_meter",
                "granularity": "window",
                "window_id": "win_0",
                "start_seconds": 0.0,
                "end_seconds": 20.0,
                "duration_seconds": 20.0,
                "confidence": 0.8,
                "limitations": [],
                "source_artifact_paths": {"performance_manifest_path": manifest.resolve().as_posix()},
                "feature_version": "ai_training_v1",
                "label_status": "raw_observation",
                "evidence_refs": [],
                "confidence_reason": "test",
                "verification_status": "unverified",
                "review_required": False,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest, feature_dir


def test_infer_subdivision_fake_patterns() -> None:
    straight = infer_subdivision_type([0.5] * 16, 1.0)
    triplet = infer_subdivision_type([0.333, 0.667] * 8, 1.0)
    swing = infer_subdivision_type([0.66, 0.34] * 8, 1.0)
    randomish = infer_subdivision_type([0.18, 0.94, 0.41, 1.17, 0.26, 0.78, 0.52], 1.0)
    sparse = infer_subdivision_type([1.0, 1.0], 1.0)
    free = infer_subdivision_type([0.7, 0.2, 1.9], 0.0)
    assert straight["subdivision_type"] == "straight"
    assert triplet["subdivision_type"] in {"triplet", "swing"}
    assert swing["subdivision_type"] in {"swing", "triplet"}
    assert randomish["subdivision_type"] in {"random", "free"}
    assert sparse["subdivision_type"] == "sparse"
    assert free["subdivision_type"] in {"sparse", "free"}


def test_extract_and_validate_meter_time_features(tmp_path: Path, monkeypatch) -> None:
    manifest, _ = _setup_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    json_path, md_path = extract_meter_time_features(manifest)
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert isinstance(payload.get("beat_meter_hypotheses"), list)
    assert len(payload["beat_meter_hypotheses"]) >= 1
    assert isinstance(payload.get("cycle_pattern_records"), list)
    assert len(payload["cycle_pattern_records"]) >= 1
    result = validate_meter_time_features(manifest)
    assert result["status"] == "success"


def test_validator_rejects_low_confidence_hard_meter(tmp_path: Path, monkeypatch) -> None:
    manifest, _ = _setup_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    json_path, _ = extract_meter_time_features(manifest)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    if isinstance(payload.get("beat_meter_hypotheses"), list) and payload["beat_meter_hypotheses"]:
        payload["beat_meter_hypotheses"][0]["meter"] = "4/4"
        payload["beat_meter_hypotheses"][0]["confidence"] = 0.2
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    result = validate_meter_time_features(manifest)
    assert result["status"] == "failed"
    assert any("low confidence" in item for item in result["errors"])


def test_export_includes_meter_time_refs(tmp_path: Path, monkeypatch) -> None:
    manifest, _ = _setup_workspace(tmp_path, performance_id="perf_meter_export")
    monkeypatch.chdir(tmp_path)
    extract_meter_time_features(manifest)
    compute_transcription_reliability(manifest)
    evaluate_training_quality_gates(manifest)
    export_dir = export_training_dataset_splits(manifest)
    accepted_lines = [line for line in (export_dir / "accepted_records.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    accepted = [json.loads(line) for line in accepted_lines]
    assert accepted
    first = accepted[0]
    assert "meter_time_refs" in first
    assert "local_tempo_bpm" in first
    assert "grid_confidence" in first
    assert "pulse_stability" in first
