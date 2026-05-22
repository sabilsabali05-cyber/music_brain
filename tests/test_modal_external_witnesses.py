from __future__ import annotations

import json
from pathlib import Path

from scripts.build_model_consensus import build_model_consensus
from scripts.compare_model_witnesses import compare_model_witnesses
from scripts.export_training_dataset_splits import export_training_dataset_splits
from scripts.run_modal_external_witnesses import run_modal_external_witnesses


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _prepare_workspace(tmp_path: Path) -> tuple[Path, Path]:
    audio_path = tmp_path / "audio" / "source.wav"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(b"RIFFfake")
    merged_midi = tmp_path / "samples" / "segments" / "source" / "run_1" / "merged" / "full_mix.mid"
    merged_midi.parent.mkdir(parents=True, exist_ok=True)
    merged_midi.write_bytes(b"MThd\x00\x00\x00\x06\x00\x00\x00\x01\x01\xe0MTrk\x00\x00\x00\x04\x00\xff\x2f\x00")
    segments_manifest = tmp_path / "samples" / "segments" / "source" / "run_1" / "segments_manifest.json"
    _write_json(
        segments_manifest,
        {
            "duration_seconds": 10.0,
            "musical_segments": [{"segment_id": "seg_0", "start_seconds": 0.0, "end_seconds": 10.0}],
            "transcription_windows": [{"window_id": "win_0", "status": "success", "core_start_seconds": 0.0, "core_end_seconds": 10.0}],
        },
    )
    perf_manifest = tmp_path / "performances" / "library" / "perf_1" / "performance_manifest.json"
    _write_json(
        perf_manifest,
        {
            "performance_id": "perf_1",
            "source_name": "source.wav",
            "source_path": audio_path.resolve().as_posix(),
            "active_segments_manifest_path": segments_manifest.resolve().as_posix(),
            "active_analysis_path": None,
            "active_merged_midi_path": merged_midi.resolve().as_posix(),
        },
    )
    feature_dir = tmp_path / "features" / "performances" / "perf_1" / "run_1"
    _write_json(feature_dir / "feature_pack_manifest.json", {"performance_id": "perf_1", "segment_run_id": "run_1"})
    _write_json(feature_dir / "rhythm_features.json", {"records": [], "summary": {}})
    _write_json(feature_dir / "harmony_features.json", {"records": [], "summary": {}})
    _write_json(feature_dir / "tags.json", {"tags": [], "top_unique_tags": []})
    _write_json(feature_dir / "rhythm_time" / "meter_time_features.json", {"beat_meter_hypotheses": []})
    _write_json(feature_dir / "pitch_harmony" / "pitch_harmony_features.json", {"macro_record": {}})
    (feature_dir / "ai_training_records.jsonl").write_text(
        json.dumps(
            {
                "record_id": "rec_0",
                "performance_id": "perf_1",
                "segment_run_id": "run_1",
                "window_id": "win_0",
                "granularity": "window",
                "start_seconds": 0.0,
                "end_seconds": 10.0,
                "duration_seconds": 10.0,
                "feature_version": "v1",
                "source_artifact_paths": {"performance_manifest_path": perf_manifest.resolve().as_posix()},
                "label_status": "raw_observation",
                "confidence": 0.8,
                "feature_refs": {},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _write_json(feature_dir / "trust" / "quality_gates.json", {"overall_quality_status": "accepted"})
    _write_json(
        feature_dir / "trust" / "transcription_reliability.json",
        {"windows": [{"window_id": "win_0", "reliability_tier": "high", "transcription_reliability_score": 0.9, "recommended_training_weight": 0.9}]},
    )
    return perf_manifest, feature_dir


def test_modal_witness_client_writes_provider_jsons(monkeypatch, tmp_path: Path) -> None:
    perf_manifest, feature_dir = _prepare_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    def _fake(provider: str, _bytes: bytes, _source_name: str):
        if provider == "essentia":
            return {"provider_name": "essentia", "status": "success", "rhythm_descriptors": {"bpm": 92.0}, "tonal_descriptors": {"key_candidates": []}}
        return {"provider_name": "music21", "status": "success", "key_candidates": [{"key": "C", "mode": "major"}], "interval_summary": {"interval_count": 3}}

    monkeypatch.setattr("scripts.run_modal_external_witnesses._invoke_modal_provider", _fake)
    summary = run_modal_external_witnesses(perf_manifest, ["essentia", "music21"])
    out_dir = Path(summary["output_dir"])
    assert (out_dir / "essentia_features.json").exists()
    assert (out_dir / "music21_features.json").exists()
    manifest = json.loads((feature_dir / "feature_pack_manifest.json").read_text(encoding="utf-8"))
    assert "external_model_feature_refs" in manifest


def test_modal_witness_unavailable_does_not_fail_pipeline(monkeypatch, tmp_path: Path) -> None:
    perf_manifest, _ = _prepare_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    def _fake(_provider: str, _bytes: bytes, _source_name: str):
        raise RuntimeError("modal unavailable")

    monkeypatch.setattr("scripts.run_modal_external_witnesses._invoke_modal_provider", _fake)
    summary = run_modal_external_witnesses(perf_manifest, ["essentia", "music21"])
    assert summary["results"]["essentia"]["status"] in {"failed", "unavailable"}
    assert summary["results"]["music21"]["status"] in {"failed", "unavailable"}


def test_consensus_consumes_essentia_music21_outputs(monkeypatch, tmp_path: Path) -> None:
    perf_manifest, feature_dir = _prepare_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    ext = feature_dir / "external_model_features"
    _write_json(ext / "essentia_features.json", {"provider_name": "essentia", "status": "success", "rhythm_descriptors": {"bpm": 100.0}, "tonal_descriptors": {"key": "C"}})
    _write_json(ext / "music21_features.json", {"provider_name": "music21", "status": "success", "key_candidates": [{"key": "C"}], "interval_summary": {"interval_count": 10}})
    _write_json(ext / "beat_tracker_features.json", {"provider_name": "beat_tracker", "status": "success", "features": {"tempo_candidates_bpm": [101.0], "meter_hypotheses": []}})
    _write_json(feature_dir / "harmony_features.json", {"records": [{"granularity": "window", "features": {"estimated_key": "C"}}], "summary": {}})
    _write_json(feature_dir / "rhythm_features.json", {"records": [{"granularity": "window", "features": {"estimated_bpm": 99.0}}], "summary": {}})
    _write_json(feature_dir / "tags.json", {"top_unique_tags": [{"tag": "energetic"}], "tags": []})
    compare_model_witnesses(perf_manifest)
    payload = build_model_consensus(perf_manifest)
    assert "agreements" in payload
    assert "provider_limitations" in payload


def test_export_includes_external_refs_without_ground_truth(monkeypatch, tmp_path: Path) -> None:
    perf_manifest, feature_dir = _prepare_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    ext = feature_dir / "external_model_features"
    _write_json(ext / "essentia_features.json", {"provider_name": "essentia", "status": "success"})
    _write_json(ext / "music21_features.json", {"provider_name": "music21", "status": "success"})
    _write_json(ext / "model_consensus.json", {"agreements": ["a"], "disagreements": ["b"], "recommended_review_items": ["r"]})
    export_dir = export_training_dataset_splits(perf_manifest)
    first_line = (export_dir / "accepted_records.jsonl").read_text(encoding="utf-8").splitlines()[0]
    first = json.loads(first_line)
    assert "external_feature_refs" in first
    assert "consensus_refs" in first
    assert first.get("label_status") != "ground_truth"
