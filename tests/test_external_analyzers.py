from __future__ import annotations

import json
from pathlib import Path

from features.external_analyzers.base import ExternalAnalyzerAvailability, ExternalAnalyzerResult
from features.external_analyzers.registry import list_external_analyzers, run_external_analyzers
from scripts.build_ai_training_records import build_ai_training_records
from scripts.build_feature_consensus import build_consensus
from scripts.compare_external_features import build_external_comparison
from scripts.extract_feature_pack import extract_feature_pack
from scripts.external_analyzer_common import run_and_write_external_analyzers


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _prepare_manifest_workspace(tmp_path: Path) -> Path:
    source_audio = tmp_path / "audio" / "source.wav"
    source_audio.parent.mkdir(parents=True, exist_ok=True)
    source_audio.write_bytes(b"RIFFfake")
    segments_manifest = tmp_path / "samples" / "segments" / "source_a" / "run_123" / "segments_manifest.json"
    _write_json(
        segments_manifest,
        {
            "duration_seconds": 10.0,
            "musical_segments": [{"segment_id": "seg_0", "start_seconds": 0.0, "end_seconds": 10.0}],
            "transcription_windows": [{"window_id": "win_0", "status": "success", "core_start_seconds": 0.0, "core_end_seconds": 10.0}],
        },
    )
    performance_manifest = tmp_path / "performances" / "library" / "perf_1" / "performance_manifest.json"
    _write_json(
        performance_manifest,
        {
            "performance_id": "perf_1",
            "source_name": "source.wav",
            "source_path": source_audio.resolve().as_posix(),
            "active_segments_manifest_path": segments_manifest.resolve().as_posix(),
            "active_analysis_path": None,
            "active_merged_midi_path": None,
        },
    )
    return performance_manifest


def _write_minimal_feature_pack(feature_dir: Path) -> None:
    _write_json(
        feature_dir / "rhythm_features.json",
        {
            "summary": {"record_count_by_granularity": {"performance": 1, "segment": 1, "window": 1, "rhythm_region": 1}},
            "records": [
                {"granularity": "performance", "features": {"estimated_bpm": 100.0}, "confidence": 0.8, "limitations": []},
                {"granularity": "segment", "window_id": "win_0", "start_seconds": 0.0, "end_seconds": 10.0, "duration_seconds": 10.0, "features": {"estimated_bpm": 100.0}, "confidence": 0.8, "limitations": []},
                {"granularity": "window", "window_id": "win_0", "start_seconds": 0.0, "end_seconds": 10.0, "duration_seconds": 10.0, "features": {"estimated_bpm": 100.0}, "confidence": 0.8, "limitations": []},
                {"granularity": "rhythm_region", "window_id": "win_0", "region_id": "r0", "start_seconds": 0.0, "end_seconds": 10.0, "duration_seconds": 10.0, "features": {"estimated_bpm": 100.0, "token_pattern": "x..x"}, "confidence": 0.8, "limitations": []},
            ],
            "rhythm_motifs": {"motifs": []},
            "rhythm_motif_groups": [],
            "rhythm_pattern_index": {"top_rhythm_family_matches": [], "unknown_high_information_patterns": [], "concept_counts": {}, "philosophy_source_counts": {}},
        },
    )
    _write_json(
        feature_dir / "harmony_features.json",
        {
            "summary": {"record_count_by_granularity": {"performance": 1, "segment": 1, "window": 1, "chord_region": 1}},
            "records": [
                {"granularity": "window", "window_id": "win_0", "start_seconds": 0.0, "end_seconds": 10.0, "duration_seconds": 10.0, "features": {"estimated_key": "C"}, "confidence": 0.8, "limitations": []},
                {"granularity": "chord_region", "window_id": "win_0", "region_id": "c0", "start_seconds": 0.0, "end_seconds": 10.0, "duration_seconds": 10.0, "features": {"estimated_key_candidates": ["C"], "chord_change_count": 1, "root_motion_intervals": [0]}, "confidence": 0.8, "limitations": []},
            ],
            "chord_movement_summary": {"active_harmonic_motion_regions": [], "repeated_chord_vamp_candidates": []},
            "harmony_pattern_index": {"repeated_chord_sequence_candidates": []},
        },
    )
    _write_json(
        feature_dir / "tags.json",
        {
            "tags": [{"window_id": "win_0", "granularity": "window", "tag": "energetic", "confidence": 0.7, "start_seconds": 0.0, "end_seconds": 10.0, "evidence": {}}],
            "grouped_tags": [{"tag": "energetic", "count": 1, "confidence_max": 0.7}],
            "top_unique_tags": [{"tag": "energetic", "count": 1, "confidence_max": 0.7, "confidence_mean": 0.7}],
        },
    )


def test_registry_lists_essentia_and_musicnn() -> None:
    providers = list_external_analyzers()
    assert "essentia" in providers
    assert "musicnn" in providers


def test_unavailable_provider_status(monkeypatch) -> None:
    class _FakeProvider:
        provider_name = "essentia"

        def check_available(self):
            return ExternalAnalyzerAvailability(provider_name="essentia", available=False, install_notes=["install me"])

    monkeypatch.setattr("features.external_analyzers.registry._provider_instances", lambda: {"essentia": _FakeProvider()})
    results = run_external_analyzers(Path("audio.wav"), {}, selected=["essentia"])
    assert len(results) == 1
    assert results[0].status == "unavailable"


def test_run_external_analyzers_writes_unavailable_json(tmp_path: Path, monkeypatch) -> None:
    manifest_path = _prepare_manifest_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "scripts.external_analyzer_common.run_external_analyzers",
        lambda *_args, **_kwargs: [
            ExternalAnalyzerResult(provider_name="essentia", status="unavailable", warnings=["missing deps"], dependency_info={"install_notes": ["pip install essentia"]}),
            ExternalAnalyzerResult(provider_name="musicnn", status="unavailable", warnings=["missing deps"], dependency_info={"install_notes": ["pip install musicnn"]}),
        ],
    )
    summary = run_and_write_external_analyzers(manifest_path, selected_providers=["essentia", "musicnn"])
    out = Path(summary["external_output_dir"])
    essentia = json.loads((out / "essentia_features.json").read_text(encoding="utf-8"))
    musicnn = json.loads((out / "musicnn_features.json").read_text(encoding="utf-8"))
    assert essentia["status"] == "unavailable"
    assert musicnn["status"] == "unavailable"


def test_feature_pack_without_external_analyzers(tmp_path: Path, monkeypatch) -> None:
    manifest_path = _prepare_manifest_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    feature_dir = tmp_path / "features" / "performances" / "perf_1" / "run_123"
    feature_dir.mkdir(parents=True, exist_ok=True)
    _write_minimal_feature_pack(feature_dir)
    _write_json(feature_dir / "feature_pack_manifest.json", {"performance_id": "perf_1", "segment_run_id": "run_123"})
    records_path = build_ai_training_records(manifest_path, output_dir=feature_dir)
    assert records_path.exists()
    first = json.loads(records_path.read_text(encoding="utf-8").splitlines()[0])
    assert "external_feature_refs" not in first


def test_feature_pack_with_external_writes_references(tmp_path: Path, monkeypatch) -> None:
    manifest_path = _prepare_manifest_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    def _fake_run(*_args, **_kwargs):
        feature_dir = tmp_path / "features" / "performances" / "perf_1" / "run_123" / "external_model_features"
        _write_json(feature_dir / "essentia_features.json", {"provider_name": "essentia", "status": "unavailable"})
        _write_json(feature_dir / "musicnn_features.json", {"provider_name": "musicnn", "status": "unavailable"})
        return {
            "results": {
                "essentia": {"status": "unavailable", "path": (feature_dir / "essentia_features.json").resolve().as_posix()},
                "musicnn": {"status": "unavailable", "path": (feature_dir / "musicnn_features.json").resolve().as_posix()},
            }
        }

    monkeypatch.setattr("scripts.extract_feature_pack.run_and_write_external_analyzers", _fake_run)
    monkeypatch.setattr("scripts.extract_feature_pack.build_external_comparison", lambda *_a, **_k: {"agreements": [], "disagreements": []})
    monkeypatch.setattr("scripts.extract_feature_pack.build_consensus", lambda *_a, **_k: {"conflict_warnings": []})
    pack_dir = extract_feature_pack(manifest_path, include_external_analyzers=True, external_providers=["essentia", "musicnn"])
    manifest = json.loads((pack_dir / "feature_pack_manifest.json").read_text(encoding="utf-8"))
    assert "external_feature_refs" in manifest
    assert "essentia_features" in manifest["external_feature_refs"]


def test_compare_external_features_handles_missing_files(tmp_path: Path, monkeypatch) -> None:
    manifest_path = _prepare_manifest_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    feature_dir = tmp_path / "features" / "performances" / "perf_1" / "run_123"
    feature_dir.mkdir(parents=True, exist_ok=True)
    _write_minimal_feature_pack(feature_dir)
    payload = build_external_comparison(manifest_path)
    assert isinstance(payload.get("agreements"), list)
    assert (feature_dir / "external_model_features" / "external_feature_comparison.json").exists()


def test_build_feature_consensus_handles_partial_providers(tmp_path: Path, monkeypatch) -> None:
    manifest_path = _prepare_manifest_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    feature_dir = tmp_path / "features" / "performances" / "perf_1" / "run_123" / "external_model_features"
    _write_json(feature_dir / "musicnn_features.json", {"provider_name": "musicnn", "status": "unavailable", "limitations": []})
    _write_json(feature_dir / "external_feature_comparison.json", {"agreements": [], "disagreements": []})
    payload = build_consensus(manifest_path)
    assert "manual_review_recommendations" in payload
    assert (feature_dir / "feature_consensus.json").exists()


def test_ai_jsonl_stores_refs_not_huge_arrays(tmp_path: Path, monkeypatch) -> None:
    manifest_path = _prepare_manifest_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    feature_dir = tmp_path / "features" / "performances" / "perf_1" / "run_123"
    feature_dir.mkdir(parents=True, exist_ok=True)
    _write_minimal_feature_pack(feature_dir)
    ext_dir = feature_dir / "external_model_features"
    _write_json(ext_dir / "essentia_features.json", {"provider_name": "essentia", "status": "success", "rhythm_descriptors": {"tempo": 100}})
    _write_json(
        ext_dir / "musicnn_features.json",
        {
            "provider_name": "musicnn",
            "status": "success",
            "top_tags": ["energetic"],
            "tag_scores": {"energetic": 0.9},
            "embedding_summary": {"dimension": 200},
            "embedding_reference": "embeddings/musicnn.npy",
            "embedding_vector": [0.123] * 2000,
        },
    )
    _write_json(ext_dir / "feature_consensus.json", {"conflict_warnings": ["tempo mismatch"]})
    records_path = build_ai_training_records(manifest_path, output_dir=feature_dir)
    first = json.loads(records_path.read_text(encoding="utf-8").splitlines()[0])
    assert "external_feature_refs" in first
    assert "external_tag_summary" in first
    assert "embedding_vector" not in json.dumps(first)

