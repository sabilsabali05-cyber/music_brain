from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_dataset_quality_yield import audit_dataset_quality_yield


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(json.dumps(row) for row in rows)
    path.write_text((body + "\n") if body else "", encoding="utf-8")


def _seed_perf(
    tmp_path: Path,
    *,
    performance_id: str,
    run_id: str,
    duration_seconds: float,
    source_records: list[dict],
    accepted_records: list[dict],
    weak_records: list[dict],
    review_records: list[dict],
    quarantined_records: list[dict],
    provider_status: dict[str, str],
) -> None:
    perf_manifest = tmp_path / "performances" / "library" / performance_id / "performance_manifest.json"
    segments_manifest = tmp_path / "samples" / "segments" / performance_id / run_id / "segments_manifest.json"
    merged_midi = tmp_path / "samples" / "segments" / performance_id / run_id / "merged" / "full_mix.mid"
    merged_midi.parent.mkdir(parents=True, exist_ok=True)
    merged_midi.write_bytes(b"MThd")
    _write_json(
        segments_manifest,
        {
            "duration_seconds": duration_seconds,
            "transcription_windows": [{"window_id": "win_0", "status": "success"}],
        },
    )
    _write_json(
        perf_manifest,
        {
            "performance_id": performance_id,
            "duration_seconds": duration_seconds,
            "active_segments_manifest_path": segments_manifest.resolve().as_posix(),
            "active_merged_midi_path": merged_midi.resolve().as_posix(),
        },
    )

    feature_dir = tmp_path / "features" / "performances" / performance_id / run_id
    export_dir = tmp_path / "datasets" / "training_exports" / performance_id / run_id
    _write_json(feature_dir / "feature_pack_manifest.json", {"performance_id": performance_id, "segment_run_id": run_id})
    _write_json(feature_dir / "rhythm_features.json", {"summary": {}})
    _write_json(feature_dir / "harmony_features.json", {"summary": {}})
    _write_json(feature_dir / "rhythm_time" / "meter_time_features.json", {"beat_meter_hypotheses": [{"meter": "4/4"}], "cycle_pattern_records": [], "phrase_rhythm_records": [], "macro_time_records": []})
    _write_json(
        feature_dir / "pitch_harmony" / "pitch_harmony_features.json",
        {
            "interval_analysis": [{"confidence": 0.8}],
            "melody_contour": [{"confidence": 0.7}],
            "counterpoint": [{"confidence": 0.6}],
            "tuning_system": [{"microtonal_analysis_available": False, "limitations": ["none"]}],
            "harmony_sonority": [{"ambiguity": 0.7}],
        },
    )
    _write_json(feature_dir / "routing" / "content_region_routes.json", {"content_state_counts": {"silence_or_noise": 1, "harmonic_dominant": 2}})
    _write_json(feature_dir / "trust" / "quality_gates.json", {"overall_quality_status": "review_required"})
    _write_json(feature_dir / "trust" / "transcription_reliability.json", {"summary": {"window_count": 1}})
    _write_json(feature_dir / "trust" / "training_data_audit.json", {"routing_and_label_upgrade_readiness": {"labels_suppressed_by_routing": 3, "upgrade_candidates": 2, "downgrade_or_suppress_candidates": 1}})
    _write_jsonl(feature_dir / "ai_training_records.jsonl", source_records)

    ext_dir = feature_dir / "external_model_features"
    for name, status in provider_status.items():
        _write_json(ext_dir / name, {"provider_name": name, "status": status})
    _write_json(ext_dir / "model_consensus.json", {"consensus_status": "conflicted", "disagreements": ["tonal mismatch"], "unresolved_conflicts": ["tonal_center_conflict"], "confidence_penalties": ["low_confidence"]})
    _write_json(ext_dir / "model_witness_comparison.json", {"provider_status": {"essentia": "success", "music21": "success"}})

    _write_jsonl(export_dir / "accepted_records.jsonl", accepted_records)
    _write_jsonl(export_dir / "weak_label_records.jsonl", weak_records)
    _write_jsonl(export_dir / "review_required_records.jsonl", review_records)
    _write_jsonl(export_dir / "quarantined_records.jsonl", quarantined_records)
    _write_jsonl(export_dir / "audio_midi_only_records.jsonl", [])
    _write_json(
        export_dir / "export_manifest.json",
        {
            "performance_id": performance_id,
            "segment_run_id": run_id,
            "source_ai_record_count": len(source_records),
            "accepted_observation_count": len(accepted_records),
            "weak_label_count": len(weak_records),
            "review_required_count": len(review_records),
            "quarantined_count": len(quarantined_records),
            "source_feature_pack_path": feature_dir.as_posix(),
        },
    )


def test_audit_reports_complete_and_incomplete_layers(tmp_path: Path, monkeypatch) -> None:
    _seed_perf(
        tmp_path,
        performance_id="perf_complete",
        run_id="run_1",
        duration_seconds=120.0,
        source_records=[{"record_id": "s1", "confidence": 0.9, "limitations": ["x"], "evidence_refs": ["a"], "model_source_refs": ["yourmt3"], "theory_source_refs": ["london"], "content_state": "harmonic_dominant"}],
        accepted_records=[{"record_id": "a1", "label_status": "raw_observation", "confidence": 0.8, "content_state": "harmonic_dominant", "local_tempo_bpm": 120.0, "pitch_class_summary": {}, "external_feature_refs": {"essentia": "x"}}],
        weak_records=[{"record_id": "w1", "label_status": "weak_label", "evidence_refs": []}],
        review_records=[{"record_id": "r1", "label_status": "review_required"}],
        quarantined_records=[],
        provider_status={
            "essentia_features.json": "success",
            "music21_features.json": "success",
            "musicnn_features.json": "unavailable",
            "beat_tracker_features.json": "unavailable",
            "omnizart_availability.json": "unavailable",
        },
    )
    # Incomplete: no export manifest and no external witness files.
    feature_dir = tmp_path / "features" / "performances" / "perf_incomplete" / "run_9"
    _write_json(feature_dir / "feature_pack_manifest.json", {"performance_id": "perf_incomplete", "segment_run_id": "run_9"})
    _write_jsonl(feature_dir / "ai_training_records.jsonl", [{"record_id": "x"}])

    monkeypatch.chdir(tmp_path)
    json_path, md_path = audit_dataset_quality_yield()
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    by_id = {f"{row['performance_id']}:{row['segment_run_id']}": row for row in payload["performance_reports"]}
    assert by_id["perf_complete:run_1"]["layer_completeness"]["training_export_present"] is True
    assert by_id["perf_incomplete:run_9"]["layer_completeness"]["training_export_present"] is False
    assert "missing_external_meter_witness" in by_id["perf_complete:run_1"]["risk_flags"]


def test_audit_computes_rates_ratios_and_flags(tmp_path: Path, monkeypatch) -> None:
    _seed_perf(
        tmp_path,
        performance_id="perf_rates",
        run_id="run_2",
        duration_seconds=60.0,
        source_records=[
            {"record_id": "s1", "confidence": 0.9, "evidence_refs": ["e1"]},
            {"record_id": "s2"},
            {"record_id": "s3"},
            {"record_id": "s4"},
            {"record_id": "s5"},
        ],
        accepted_records=[{"record_id": "a1", "label_status": "raw_observation"}],
        weak_records=[{"record_id": "w1", "label_status": "weak_label", "evidence_refs": []}, {"record_id": "w2", "label_status": "weak_label", "evidence_refs": []}],
        review_records=[{"record_id": "r1"}, {"record_id": "r2"}],
        quarantined_records=[],
        provider_status={
            "essentia_features.json": "success",
            "music21_features.json": "success",
            "musicnn_features.json": "unavailable",
            "beat_tracker_features.json": "unavailable",
            "omnizart_availability.json": "unavailable",
        },
    )
    monkeypatch.chdir(tmp_path)
    json_path, _ = audit_dataset_quality_yield()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    perf = next(row for row in payload["performance_reports"] if row["performance_id"] == "perf_rates")
    assert perf["basic_yield"]["records_per_minute"] == 5.0
    assert perf["basic_yield"]["accepted_observations_per_minute"] == 1.0
    assert perf["trust_quality"]["ratios"]["accepted_ratio_pct"] == 20.0
    assert perf["trust_quality"]["ratios"]["weak_ratio_pct"] == 40.0
    assert perf["trust_quality"]["ratios"]["review_ratio_pct"] == 40.0
    assert "weak_labels_without_evidence" in perf["risk_flags"]


def test_audit_flags_hard_labels_without_confidence_and_no_audio_processing(tmp_path: Path, monkeypatch) -> None:
    audio = tmp_path / "audio" / "source.wav"
    audio.parent.mkdir(parents=True, exist_ok=True)
    audio.write_bytes(b"RIFFstatic")

    _seed_perf(
        tmp_path,
        performance_id="perf_conf",
        run_id="run_3",
        duration_seconds=30.0,
        source_records=[{"record_id": "s1"}],
        accepted_records=[{"record_id": "a1", "label_status": "raw_observation", "confidence": None}],
        weak_records=[],
        review_records=[{"record_id": "r1"}],
        quarantined_records=[],
        provider_status={
            "essentia_features.json": "success",
            "music21_features.json": "success",
            "musicnn_features.json": "unavailable",
            "beat_tracker_features.json": "unavailable",
            "omnizart_availability.json": "unavailable",
        },
    )

    before = audio.read_bytes()
    monkeypatch.chdir(tmp_path)
    json_path, _ = audit_dataset_quality_yield()
    after = audio.read_bytes()
    assert before == after

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    perf = next(row for row in payload["performance_reports"] if row["performance_id"] == "perf_conf")
    assert "hard_labels_without_confidence" in perf["risk_flags"]
