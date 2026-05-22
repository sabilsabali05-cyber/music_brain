from __future__ import annotations

import json
from pathlib import Path

from mido import Message, MidiFile, MidiTrack

from features.trust.failure_taxonomy import make_failure_record
from features.trust.field_trust_policy import (
    classify_record_for_export,
    make_accepted_observation_record,
    should_quarantine_record,
)
from scripts.audit_training_dataset_record import audit_training_dataset_record
from scripts.compute_transcription_reliability import compute_transcription_reliability
from scripts.evaluate_training_quality_gates import evaluate_training_quality_gates
from scripts.export_training_dataset_splits import export_training_dataset_splits
from scripts.validate_training_export import validate_training_export


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


def _setup_workspace(tmp_path: Path) -> tuple[Path, Path]:
    source_audio = tmp_path / "audio" / "source.wav"
    source_audio.parent.mkdir(parents=True, exist_ok=True)
    source_audio.write_bytes(b"RIFFfake")

    run_dir = tmp_path / "samples" / "segments" / "source_a" / "run_123"
    midi_ok = run_dir / "windows" / "win_0.mid"
    _write_midi(midi_ok, [60, 64, 67, 72, 74, 76, 79, 81, 83, 84], spacing_ticks=90)
    segments_manifest = run_dir / "segments_manifest.json"
    _write_json(
        segments_manifest,
        {
            "duration_seconds": 20.0,
            "transcription_windows": [
                {
                    "window_id": "win_0",
                    "status": "success",
                    "core_start_seconds": 0.0,
                    "core_end_seconds": 10.0,
                    "midi_path": midi_ok.resolve().as_posix(),
                },
                {
                    "window_id": "win_1",
                    "status": "success",
                    "core_start_seconds": 10.0,
                    "core_end_seconds": 20.0,
                    "midi_path": (run_dir / "windows" / "missing.mid").resolve().as_posix(),
                },
            ],
        },
    )
    manifest = tmp_path / "performances" / "library" / "perf_1" / "performance_manifest.json"
    _write_json(
        manifest,
        {
            "performance_id": "perf_1",
            "source_name": "source.wav",
            "source_path": source_audio.resolve().as_posix(),
            "duration_seconds": 20.0,
            "active_segments_manifest_path": segments_manifest.resolve().as_posix(),
            "active_analysis_path": None,
            "active_merged_midi_path": None,
        },
    )

    feature_dir = tmp_path / "features" / "performances" / "perf_1" / "run_123"
    _write_json(
        feature_dir / "rhythm_features.json",
        {
            "summary": {"record_count_by_granularity": {"performance": 1, "segment": 1, "window": 1, "rhythm_region": 1}},
            "records": [{"granularity": "window", "window_id": "win_0", "features": {"estimated_bpm": 100}, "confidence": 0.8, "limitations": []}],
            "rhythm_motifs": {"motif_count": 1, "motifs": []},
            "rhythm_motif_groups": [],
            "rhythm_pattern_index": {
                "rhythm_family_counts": {},
                "strong_rhythm_family_counts": {},
                "moderate_rhythm_family_counts": {},
                "weak_rhythm_family_counts": {},
                "raw_candidate_match_counts": {},
                "motif_group_family_counts": {},
                "strong_group_family_counts": {},
                "ambiguous_rhythm_family_count": 0,
                "top_rhythm_family_matches": [],
                "unknown_high_information_patterns": [],
                "concept_counts": {},
                "philosophy_source_counts": {},
            },
        },
    )
    _write_json(
        feature_dir / "harmony_features.json",
        {
            "summary": {"record_count_by_granularity": {"performance": 1, "segment": 1, "window": 1, "chord_region": 1}},
            "records": [{"granularity": "window", "window_id": "win_0", "features": {"estimated_key": "C"}, "confidence": 0.8, "limitations": []}],
            "chord_movement_summary": {},
            "harmony_pattern_index": {},
        },
    )
    _write_json(
        feature_dir / "tags.json",
        {
            "tags": [
                {
                    "tag": "dense_region",
                    "confidence": 0.8,
                    "evidence": {"metric": "density"},
                    "label_status": "heuristic_estimate",
                    "evidence_refs": [],
                    "confidence_reason": "test",
                    "verification_status": "unverified",
                    "review_required": True,
                }
            ],
            "grouped_tags": [{"tag": "dense_region", "count": 1, "confidence_max": 0.8, "confidence_mean": 0.8}],
            "top_unique_tags": [{"tag": "dense_region", "count": 1, "confidence_max": 0.8, "confidence_mean": 0.8}],
            "tag_count": 1,
        },
    )
    _write_json(
        feature_dir / "feature_pack_manifest.json",
        {
            "performance_id": "perf_1",
            "segment_run_id": "run_123",
            "feature_pack_dir": feature_dir.resolve().as_posix(),
        },
    )
    ai_lines = [
        json.dumps(
            {
                "record_id": "r1",
                "performance_id": "perf_1",
                "granularity": "window",
                "window_id": "win_0",
                "start_seconds": 0.0,
                "end_seconds": 10.0,
                "confidence": 0.82,
                "limitations": [],
                "source_artifact_paths": {},
                "feature_version": "ai_training_v1",
                "label_status": "raw_observation",
                "evidence_refs": [],
                "confidence_reason": "test",
                "verification_status": "unverified",
                "review_required": False,
            }
        ),
        json.dumps(
            {
                "record_id": "r2",
                "performance_id": "perf_1",
                "granularity": "window",
                "window_id": "win_1",
                "start_seconds": 10.0,
                "end_seconds": 20.0,
                "confidence": 0.4,
                "limitations": [],
                "source_artifact_paths": {},
                "feature_version": "ai_training_v1",
                "label_status": "weak_label",
                "evidence_refs": [],
                "confidence_reason": "test",
                "verification_status": "unverified",
                "review_required": True,
            }
        ),
    ]
    (feature_dir / "ai_training_records.jsonl").write_text("\n".join(ai_lines) + "\n", encoding="utf-8")
    summary = "\n".join(
        [
            "rhythm_record_count_by_granularity",
            "harmony_record_count_by_granularity",
            "ai_record_count_by_granularity",
            "Top Unique Tags",
            "Rhythm Motif Candidates",
            "Top Rhythm Motif Groups",
            "Harmony Pattern Index",
            "Rhythm Philosophy Interpretation",
            "Standard Rhythm Family Matches",
            "Rhythm Family Classification Quality",
            "Standard Rhythm Lexicon Review",
        ]
    )
    (feature_dir / "feature_summary.md").write_text(summary, encoding="utf-8")
    return manifest, feature_dir


def test_transcription_reliability_scores_and_missing_midi(tmp_path: Path, monkeypatch) -> None:
    manifest, _ = _setup_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    output = compute_transcription_reliability(manifest)
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert isinstance(payload.get("windows"), list)
    tiers = {item["window_id"]: item["reliability_tier"] for item in payload["windows"] if isinstance(item, dict)}
    assert tiers.get("win_0") in {"high", "medium"}
    assert tiers.get("win_1") == "missing"


def test_quality_gates_and_audit_write_outputs(tmp_path: Path, monkeypatch) -> None:
    manifest, feature_dir = _setup_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    compute_transcription_reliability(manifest)
    gates_path = evaluate_training_quality_gates(manifest)
    gates = json.loads(gates_path.read_text(encoding="utf-8"))
    assert "overall_quality_status" in gates
    audit_md, audit_json = audit_training_dataset_record(manifest)
    assert audit_md.exists()
    assert audit_json.exists()
    assert feature_dir.exists()


def test_export_splits_and_no_weak_as_accepted(tmp_path: Path, monkeypatch) -> None:
    manifest, _ = _setup_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    compute_transcription_reliability(manifest)
    evaluate_training_quality_gates(manifest)
    export_dir = export_training_dataset_splits(manifest)
    accepted = (export_dir / "accepted_records.jsonl").read_text(encoding="utf-8")
    assert '"source_record_id": "r2"' not in accepted
    weak_labels = (export_dir / "weak_label_records.jsonl").read_text(encoding="utf-8")
    assert '"source_record_id": "r2"' in weak_labels
    summary = validate_training_export(export_dir)
    assert summary["status"] == "success"


def test_field_policy_high_reliability_mixed_record_yields_observation_and_weak(tmp_path: Path, monkeypatch) -> None:
    manifest, _ = _setup_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    compute_transcription_reliability(manifest)
    gates_path = evaluate_training_quality_gates(manifest)
    gates = json.loads(gates_path.read_text(encoding="utf-8"))
    gates["overall_quality_status"] = "accepted"
    gates["recommended_dataset_split"] = "train"
    gates_path.write_text(json.dumps(gates, indent=2), encoding="utf-8")
    export_dir = export_training_dataset_splits(manifest)
    accepted_records = [json.loads(line) for line in (export_dir / "accepted_records.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    weak_records = [json.loads(line) for line in (export_dir / "weak_label_records.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    assert any(item.get("source_record_id") == "r1" for item in accepted_records)
    assert any(item.get("source_record_id") == "r2" for item in weak_records)
    for item in accepted_records:
        assert item.get("label_status") in {"raw_observation", "derived_observation", "human_verified_label"}
        assert "weak_fields" not in item


def test_field_policy_classification_helpers() -> None:
    record = {
        "record_id": "x1",
        "performance_id": "perf",
        "segment_run_id": "run",
        "granularity": "window",
        "start_seconds": 0.0,
        "end_seconds": 2.0,
        "label_status": "raw_observation",
        "confidence": 0.8,
        "feature_version": "ai_training_v1",
        "source_artifact_paths": {"performance_manifest_path": "a.json"},
        "input_features": {"rhythm_excerpt": {"note_on_count": 30, "note_density_per_second": 4.0}},
    }
    rel_lookup = {"win_0": {"reliability_tier": "high", "transcription_reliability_score": 0.95, "recommended_training_weight": 1.0}}
    record["window_id"] = "win_0"
    classification = classify_record_for_export(record, rel_lookup, {"overall_quality_status": "accepted"})
    assert classification["split"] == "accepted_records"
    accepted, excluded = make_accepted_observation_record(record, rel_lookup)
    assert accepted["record_id"] == "x1"
    assert isinstance(excluded, list)
    quarantine, reasons = should_quarantine_record(record)
    assert quarantine is False
    assert reasons == []


def test_malformed_records_go_quarantine(tmp_path: Path, monkeypatch) -> None:
    manifest, feature_dir = _setup_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    (feature_dir / "ai_training_records.jsonl").write_text(
        json.dumps({"performance_id": "perf_1", "start_seconds": 5.0, "end_seconds": 1.0}) + "\n",
        encoding="utf-8",
    )
    compute_transcription_reliability(manifest)
    evaluate_training_quality_gates(manifest)
    export_dir = export_training_dataset_splits(manifest)
    quarantined_records = [json.loads(line) for line in (export_dir / "quarantined_records.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(quarantined_records) >= 1


def test_validate_training_export_catches_malformed_jsonl(tmp_path: Path) -> None:
    export_dir = tmp_path / "datasets" / "training_exports" / "perf_1" / "run_123"
    export_dir.mkdir(parents=True, exist_ok=True)
    for name in [
        "accepted_records.jsonl",
        "weak_label_records.jsonl",
        "audio_midi_only_records.jsonl",
        "review_required_records.jsonl",
        "quarantined_records.jsonl",
    ]:
        (export_dir / name).write_text("{bad json}\n", encoding="utf-8")
    _write_json(export_dir / "export_manifest.json", {"counts_per_split": {}})
    summary = validate_training_export(export_dir)
    assert summary["status"] == "failed"


def test_validator_rejects_accepted_with_weak_fields(tmp_path: Path) -> None:
    export_dir = tmp_path / "datasets" / "training_exports" / "perf_1" / "run_123"
    export_dir.mkdir(parents=True, exist_ok=True)
    accepted_record = {
        "export_record_id": "x",
        "source_record_id": "r1",
        "record_id": "r1",
        "performance_id": "perf_1",
        "granularity": "window",
        "start_seconds": 0.0,
        "end_seconds": 1.0,
        "label_status": "weak_label",
        "best_rhythm_family_match": "tresillo_3_3_2",
        "export_split": "accepted_records",
    }
    (export_dir / "accepted_records.jsonl").write_text(json.dumps(accepted_record) + "\n", encoding="utf-8")
    for name in [
        "weak_label_records.jsonl",
        "audio_midi_only_records.jsonl",
        "review_required_records.jsonl",
        "quarantined_records.jsonl",
    ]:
        (export_dir / name).write_text("", encoding="utf-8")
    _write_json(
        export_dir / "export_manifest.json",
        {
            "counts_per_split": {
                "accepted_records": 1,
                "weak_label_records": 0,
                "audio_midi_only_records": 0,
                "review_required_records": 0,
                "quarantined_records": 0,
            },
            "accepted_observation_count": 1,
            "weak_label_count": 0,
            "audio_midi_only_count": 0,
            "review_required_count": 0,
            "quarantined_count": 0,
        },
    )
    summary = validate_training_export(export_dir)
    assert summary["status"] == "failed"


def test_failure_taxonomy_record_shape() -> None:
    payload = make_failure_record(
        stage="validation",
        category="schema_failure",
        severity="critical",
        message="bad schema",
        artifact_path="features/file.json",
    )
    for key in ["stage", "category", "severity", "message", "recoverable", "created_at"]:
        assert key in payload
