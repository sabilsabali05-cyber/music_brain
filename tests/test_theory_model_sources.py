from __future__ import annotations

import json
from pathlib import Path

from features.model_sources import MODEL_SOURCES, get_model_source, list_model_sources
from features.theory_sources import THEORY_SOURCES, get_theory_sources_for_concept
from features.external_analyzers.base import ExternalAnalyzerResult
from scripts.audit_training_dataset_record import audit_training_dataset_record
from scripts.build_model_consensus import build_model_consensus
from scripts.export_training_dataset_splits import export_training_dataset_splits
from scripts.external_analyzer_common import run_and_write_external_analyzers


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _prepare_workspace(tmp_path: Path) -> tuple[Path, Path]:
    source_audio = tmp_path / "audio" / "source.wav"
    source_audio.parent.mkdir(parents=True, exist_ok=True)
    source_audio.write_bytes(b"RIFFfake")
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
            "source_path": source_audio.resolve().as_posix(),
            "active_segments_manifest_path": segments_manifest.resolve().as_posix(),
            "active_analysis_path": None,
            "active_merged_midi_path": None,
        },
    )
    feature_dir = tmp_path / "features" / "performances" / "perf_1" / "run_1"
    feature_dir.mkdir(parents=True, exist_ok=True)
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
    _write_json(feature_dir / "rhythm_features.json", {"records": [], "summary": {}})
    _write_json(feature_dir / "harmony_features.json", {"records": [], "summary": {}})
    _write_json(feature_dir / "tags.json", {"tags": [], "top_unique_tags": []})
    _write_json(feature_dir / "feature_pack_manifest.json", {"performance_id": "perf_1", "segment_run_id": "run_1"})
    return perf_manifest, feature_dir


def test_theory_registry_covers_required_domains() -> None:
    assert get_theory_sources_for_concept("meter")
    assert get_theory_sources_for_concept("microtiming")
    assert get_theory_sources_for_concept("counterpoint")
    assert any("microtonality" in [str(v).lower() for v in item.get("concepts", [])] for item in THEORY_SOURCES)


def test_model_registry_contains_required_providers_and_policies() -> None:
    ids = {str(item.get("provider_id")) for item in list_model_sources()}
    for required in [
        "yourmt3",
        "pretty_midi",
        "librosa",
        "essentia",
        "beatnet",
        "madmom",
        "beat_tracker",
        "music21",
        "musicnn",
        "essentia_tf",
        "omnizart",
        "groove_midi_dataset",
    ]:
        assert required in ids
    assert all(bool(item.get("trust_policy")) for item in MODEL_SOURCES)
    assert get_model_source("yourmt3") is not None


def test_run_external_witnesses_writes_unavailable_json(tmp_path: Path, monkeypatch) -> None:
    perf_manifest, feature_dir = _prepare_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "scripts.external_analyzer_common.run_external_analyzers",
        lambda *_a, **_k: [
            ExternalAnalyzerResult(provider_name="essentia", status="unavailable", warnings=["missing deps"])
        ],
    )
    summary = run_and_write_external_analyzers(perf_manifest, selected_providers=["essentia", "musicnn", "beat_tracker", "music21", "omnizart"])
    assert Path(summary["external_output_dir"]).exists()
    payload = json.loads((Path(summary["external_output_dir"]) / "essentia_features.json").read_text(encoding="utf-8"))
    assert payload["status"] == "unavailable"


def test_consensus_handles_missing_providers(tmp_path: Path, monkeypatch) -> None:
    perf_manifest, feature_dir = _prepare_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    external_dir = feature_dir / "external_model_features"
    _write_json(external_dir / "model_witness_comparison.json", {})
    payload = build_model_consensus(perf_manifest)
    assert "agreements" in payload
    assert "disagreements" in payload
    assert payload.get("consensus_is_not_ground_truth") is True


def test_audit_and_export_include_model_theory_refs(tmp_path: Path, monkeypatch) -> None:
    perf_manifest, feature_dir = _prepare_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    export_dir = export_training_dataset_splits(perf_manifest)
    manifest = json.loads((export_dir / "export_manifest.json").read_text(encoding="utf-8"))
    assert "model_sources_used" in manifest
    assert "theory_sources_used" in manifest
    assert "consensus_status" in manifest
    _, audit_json_path = audit_training_dataset_record(perf_manifest)
    audit_payload = json.loads(Path(audit_json_path).read_text(encoding="utf-8"))
    assert "theory_and_model_source_coverage" in audit_payload
    first = None
    for name in ["accepted_records.jsonl", "audio_midi_only_records.jsonl", "review_required_records.jsonl", "weak_label_records.jsonl"]:
        lines = (export_dir / name).read_text(encoding="utf-8").splitlines()
        if lines:
            first = json.loads(lines[0])
            break
    assert first is not None
    assert "model_source_refs" in first
    assert "theory_source_refs" in first
    assert first.get("label_status") != "ground_truth"
