from __future__ import annotations

import json
from pathlib import Path

from mido import Message, MidiFile, MidiTrack

from scripts.export_training_dataset_splits import export_training_dataset_splits
from scripts.extract_pitch_harmony_features import (
    _motion_metrics,
    classify_sonority_type,
    extract_pitch_harmony_features,
)
from scripts.validate_pitch_harmony_features import validate_pitch_harmony_features


def _write_midi(path: Path, notes: list[int], *, with_pitch_bend: bool = False) -> None:
    midi = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    midi.tracks.append(track)
    for idx, note in enumerate(notes):
        if with_pitch_bend and idx == 1:
            track.append(Message("pitchwheel", pitch=512, time=0))
        track.append(Message("note_on", note=note, velocity=80, time=90))
        track.append(Message("note_off", note=note, velocity=0, time=90))
    path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(path)


def _write_manifest_workspace(tmp_path: Path, *, with_pitch_bend: bool = False) -> Path:
    midi_path = tmp_path / "samples" / "segments" / "source" / "run_123" / "merged" / "merged_performance.mid"
    _write_midi(midi_path, [60, 64, 67, 72, 76, 79], with_pitch_bend=with_pitch_bend)
    segments_manifest = tmp_path / "samples" / "segments" / "source" / "run_123" / "segments_manifest.json"
    segments_manifest.parent.mkdir(parents=True, exist_ok=True)
    segments_manifest.write_text(
        json.dumps(
            {
                "duration_seconds": 30.0,
                "transcription_windows": [
                    {
                        "window_id": "win_0000",
                        "status": "success",
                        "core_start_seconds": 0.0,
                        "core_end_seconds": 10.0,
                        "midi_path": midi_path.as_posix(),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    performance_manifest = tmp_path / "performances" / "library" / "perf_1" / "performance_manifest.json"
    performance_manifest.parent.mkdir(parents=True, exist_ok=True)
    performance_manifest.write_text(
        json.dumps(
            {
                "performance_id": "perf_1",
                "source_name": "fake.wav",
                "duration_seconds": 30.0,
                "active_segments_manifest_path": segments_manifest.resolve().as_posix(),
                "active_analysis_path": None,
                "active_merged_midi_path": midi_path.resolve().as_posix(),
            }
        ),
        encoding="utf-8",
    )
    return performance_manifest


def test_sonority_candidates_cover_triads_quartal_clusters() -> None:
    assert classify_sonority_type([0, 4, 7]) == "triadic_sonority_candidate"
    assert classify_sonority_type([0, 5, 10]) == "quartal_sonority_candidate"
    assert classify_sonority_type([0, 1, 2, 6, 7]) == "cluster_sonority_candidate"


def test_chromatic_motion_metric_rises() -> None:
    low = _motion_metrics([5, 7, 0, 5], [5, 5, 0, 5])
    high = _motion_metrics([1, 11, 1, 11], [1, 1, 1, 1])
    assert high["chromatic_motion_score"] > low["chromatic_motion_score"]


def test_extract_pitch_harmony_microtonal_evidence_from_pitch_bend(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    manifest = _write_manifest_workspace(tmp_path, with_pitch_bend=True)
    output_path = extract_pitch_harmony_features(manifest)
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["microtonal_analysis_available"] is True
    assert payload["microtonal_evidence_type"] == "pitch_bend"
    assert float(payload["microtonal_confidence"]) > 0.0


def test_extract_pitch_harmony_no_pitch_bend_does_not_overclaim(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    manifest = _write_manifest_workspace(tmp_path, with_pitch_bend=False)
    output_path = extract_pitch_harmony_features(manifest)
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["microtonal_evidence_type"] in {"external_analyzer_required", "unavailable"}
    assert float(payload["microtonal_confidence"]) <= 0.2


def test_counterpoint_and_common_tones_present(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    manifest = _write_manifest_workspace(tmp_path, with_pitch_bend=False)
    output_path = extract_pitch_harmony_features(manifest)
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    movement = payload["chord_movement"][0]
    counterpoint = payload["counterpoint"][0]
    assert int(movement["common_tone_count"]) >= 0
    assert float(counterpoint["motion_proxy_summary"]["contrary_motion_proxy"]) >= 0.0


def test_validator_rejects_hard_key_claim_without_confidence(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    manifest = _write_manifest_workspace(tmp_path, with_pitch_bend=False)
    output_path = extract_pitch_harmony_features(manifest)
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    payload["macro_record"]["key_hypotheses"] = [{"label": "major", "confidence": 0.2}]
    output_path.write_text(json.dumps(payload), encoding="utf-8")
    summary = validate_pitch_harmony_features(manifest)
    assert summary["status"] == "failed"


def test_export_records_reference_pitch_harmony_feature_path(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    manifest = _write_manifest_workspace(tmp_path, with_pitch_bend=False)
    output_path = extract_pitch_harmony_features(manifest)
    feature_dir = output_path.parents[1]
    trust_dir = feature_dir / "trust"
    trust_dir.mkdir(parents=True, exist_ok=True)
    (trust_dir / "quality_gates.json").write_text(json.dumps({"overall_quality_status": "accepted"}), encoding="utf-8")
    (trust_dir / "transcription_reliability.json").write_text(
        json.dumps(
            {
                "windows": [
                    {
                        "window_id": "win_0000",
                        "reliability_tier": "high",
                        "transcription_reliability_score": 0.95,
                        "recommended_training_weight": 1.0,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (feature_dir / "ai_training_records.jsonl").write_text(
        json.dumps(
            {
                "record_id": "r1",
                "performance_id": "perf_1",
                "segment_run_id": "run_123",
                "granularity": "window",
                "window_id": "win_0000",
                "start_seconds": 0.0,
                "end_seconds": 10.0,
                "confidence": 0.8,
                "label_status": "raw_observation",
                "source_artifact_paths": {},
                "feature_version": "ai_training_v1",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    export_dir = export_training_dataset_splits(manifest)
    accepted = (export_dir / "accepted_records.jsonl").read_text(encoding="utf-8")
    assert "pitch_harmony_features_path" in accepted
