from __future__ import annotations

import json
from pathlib import Path

from scripts.apply_analysis_routing import apply_analysis_routing
from scripts.audit_training_dataset_record import audit_training_dataset_record
from scripts.classify_audio_asset import classify_audio_asset
from scripts.classify_content_regions import classify_content_regions
from scripts.evaluate_label_upgrade_candidates import evaluate_label_upgrade_candidates
from scripts.export_training_dataset_splits import export_training_dataset_splits
from scripts.feature_dataset_common import default_feature_dir


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def _setup_workspace(tmp_path: Path) -> tuple[Path, Path]:
    performance_id = "perf_route_1"
    run_id = "run_001"
    segments_path = tmp_path / "samples" / "segments" / "src" / run_id / "segments_manifest.json"
    _write_json(
        segments_path,
        {
            "duration_seconds": 32.0,
            "musical_segments": [
                {"segment_id": "seg_0", "global_start_seconds": 0.0, "global_end_seconds": 8.0},
                {"segment_id": "seg_1", "global_start_seconds": 8.0, "global_end_seconds": 16.0},
                {"segment_id": "seg_2", "global_start_seconds": 16.0, "global_end_seconds": 24.0},
                {"segment_id": "seg_3", "global_start_seconds": 24.0, "global_end_seconds": 32.0},
            ],
            "transcription_windows": [
                {"window_id": "win_0", "status": "success", "core_start_seconds": 0.0, "core_end_seconds": 16.0},
                {"window_id": "win_1", "status": "success", "core_start_seconds": 16.0, "core_end_seconds": 32.0},
            ],
        },
    )
    manifest_path = tmp_path / "performances" / "library" / performance_id / "performance_manifest.json"
    _write_json(
        manifest_path,
        {
            "performance_id": performance_id,
            "source_name": "route_source.wav",
            "source_path": (tmp_path / "audio" / "route_source.wav").as_posix(),
            "duration_seconds": 32.0,
            "active_segments_manifest_path": segments_path.resolve().as_posix(),
            "active_analysis_path": None,
            "active_merged_midi_path": None,
        },
    )
    feature_dir = default_feature_dir(performance_id, run_id)
    _write_json(
        feature_dir / "rhythm_features.json",
        {
            "records": [
                {
                    "record_id": "rr_perc",
                    "granularity": "rhythm_region",
                    "window_id": "win_0",
                    "region_id": "region_perc",
                    "start_seconds": 0.0,
                    "end_seconds": 8.0,
                    "features": {
                        "note_on_count": 48,
                        "note_on_density_per_second": 4.2,
                        "polyphonic_density": 0.03,
                        "silence_ratio": 0.08,
                    },
                },
                {
                    "record_id": "rr_ambient",
                    "granularity": "rhythm_region",
                    "window_id": "win_1",
                    "region_id": "region_ambient",
                    "start_seconds": 16.0,
                    "end_seconds": 24.0,
                    "features": {
                        "note_on_count": 2,
                        "note_on_density_per_second": 0.2,
                        "polyphonic_density": 0.0,
                        "silence_ratio": 0.9,
                    },
                },
                {
                    "record_id": "rr_rhythm",
                    "granularity": "rhythm_region",
                    "window_id": "win_1",
                    "region_id": "region_rhythm",
                    "start_seconds": 24.0,
                    "end_seconds": 32.0,
                    "features": {
                        "note_on_count": 22,
                        "note_on_density_per_second": 2.4,
                        "polyphonic_density": 0.08,
                        "silence_ratio": 0.25,
                    },
                },
            ]
        },
    )
    _write_json(
        feature_dir / "harmony_features.json",
        {
            "records": [
                {
                    "record_id": "cr_harm",
                    "granularity": "chord_region",
                    "window_id": "win_0",
                    "region_id": "region_harm",
                    "start_seconds": 8.0,
                    "end_seconds": 16.0,
                    "confidence": 0.88,
                    "features": {
                        "note_on_count": 30,
                        "chord_change_count": 3,
                        "repeated_root": 0.25,
                        "pitch_class_histogram": [5, 0, 2, 0, 6, 1, 0, 4, 0, 1, 0, 3],
                    },
                }
            ]
        },
    )
    _write_json(
        feature_dir / "tags.json",
        {
            "tags": [
                {"tag": "drum_heavy", "start_seconds": 0.0, "end_seconds": 8.0, "confidence": 0.8},
                {"tag": "ambient_texture", "start_seconds": 16.0, "end_seconds": 24.0, "confidence": 0.8},
                {"tag": "rhythm_family_tresillo_3_3_2", "start_seconds": 24.0, "end_seconds": 32.0, "confidence": 0.9},
            ]
        },
    )
    _write_jsonl(
        feature_dir / "ai_training_records.jsonl",
        [
            {
                "record_id": "obs_win_0",
                "performance_id": performance_id,
                "segment_run_id": run_id,
                "granularity": "window",
                "window_id": "win_0",
                "start_seconds": 0.0,
                "end_seconds": 16.0,
                "confidence": 0.85,
                "label_status": "raw_observation",
                "source_artifact_paths": {"performance_manifest_path": manifest_path.resolve().as_posix()},
                "feature_version": "ai_training_v1",
                "limitations": [],
                "evidence_refs": [],
                "confidence_reason": "test",
                "verification_status": "unverified",
                "review_required": False,
                "input_features": {"rhythm_excerpt": {"note_on_count": 32, "note_density_per_second": 2.0}},
            },
            {
                "record_id": "weak_chord_perc",
                "performance_id": performance_id,
                "segment_run_id": run_id,
                "granularity": "rhythm_region",
                "window_id": "win_0",
                "start_seconds": 0.0,
                "end_seconds": 8.0,
                "confidence": 0.72,
                "label_status": "weak_label",
                "label": "chord_label_candidate",
                "source_artifact_paths": {"performance_manifest_path": manifest_path.resolve().as_posix()},
                "feature_version": "ai_training_v1",
                "limitations": [],
                "evidence_refs": [],
                "confidence_reason": "test",
                "verification_status": "unverified",
                "review_required": True,
            },
            {
                "record_id": "weak_rhythm_region",
                "performance_id": performance_id,
                "segment_run_id": run_id,
                "granularity": "rhythm_region",
                "window_id": "win_1",
                "start_seconds": 24.0,
                "end_seconds": 32.0,
                "confidence": 0.81,
                "label_status": "weak_label",
                "label": "rhythm_family_match",
                "source_artifact_paths": {"performance_manifest_path": manifest_path.resolve().as_posix()},
                "feature_version": "ai_training_v1",
                "limitations": [],
                "evidence_refs": [],
                "confidence_reason": "test",
                "verification_status": "unverified",
                "review_required": True,
            },
        ],
    )
    _write_json(
        feature_dir / "trust" / "transcription_reliability.json",
        {
            "windows": [
                {
                    "window_id": "win_0",
                    "transcription_reliability_score": 0.9,
                    "reliability_tier": "high",
                    "recommended_training_weight": 1.0,
                },
                {
                    "window_id": "win_1",
                    "transcription_reliability_score": 0.85,
                    "reliability_tier": "high",
                    "recommended_training_weight": 0.95,
                },
            ],
            "summary": {"window_count": 2},
        },
    )
    _write_json(
        feature_dir / "trust" / "quality_gates.json",
        {
            "overall_quality_status": "accepted",
            "recommended_dataset_split": "train",
        },
    )
    _write_json(feature_dir / "feature_pack_manifest.json", {"performance_id": performance_id, "segment_run_id": run_id})
    return manifest_path, feature_dir


def _run_routing_pipeline(manifest_path: Path) -> None:
    classify_audio_asset(manifest_path)
    classify_content_regions(manifest_path)
    apply_analysis_routing(manifest_path)
    evaluate_label_upgrade_candidates(manifest_path)


def test_routing_state_rules_and_family_suppression(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    manifest_path, feature_dir = _setup_workspace(tmp_path)
    _run_routing_pipeline(manifest_path)
    decisions = json.loads((feature_dir / "routing" / "analysis_routing_decisions.json").read_text(encoding="utf-8"))
    rows = decisions.get("decisions", [])
    by_state = {str(item.get("content_state")): item for item in rows if isinstance(item, dict)}
    assert "hard_chord_label" in by_state["percussive_only"]["suppressed_labels"]
    assert "chord_label_candidate" in by_state["harmonic_dominant"]["allowed_labels"]
    assert "hard_tempo_label" in by_state["ambient_low_information"]["suppressed_labels"]
    assert isinstance(by_state["percussive_only"]["allowed_feature_families"], list)
    assert isinstance(by_state["percussive_only"]["suppressed_feature_families"], list)


def test_label_upgrade_candidates_follow_content_state(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    manifest_path, feature_dir = _setup_workspace(tmp_path)
    _run_routing_pipeline(manifest_path)
    payload = json.loads((feature_dir / "trust" / "label_upgrade_candidates.json").read_text(encoding="utf-8"))
    candidates = payload.get("candidates", [])
    by_source = {str(item.get("source_label_id")): item for item in candidates if isinstance(item, dict)}
    assert by_source["weak_chord_perc"]["recommended_label_status"] in {"downgrade_candidate", "suppress_candidate"}
    assert by_source["weak_rhythm_region"]["recommended_label_status"] == "upgrade_candidate"


def test_export_and_audit_include_routing_upgrade_refs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    manifest_path, feature_dir = _setup_workspace(tmp_path)
    _run_routing_pipeline(manifest_path)
    export_dir = export_training_dataset_splits(manifest_path)
    accepted_lines = [json.loads(line) for line in (export_dir / "accepted_records.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    weak_lines = [json.loads(line) for line in (export_dir / "weak_label_records.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    review_lines = [json.loads(line) for line in (export_dir / "review_required_records.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    assert any("content_state" in item and "route_confidence" in item for item in accepted_lines)
    assert any("label_upgrade_candidate_refs" in item for item in weak_lines + review_lines)

    audit_md, audit_json = audit_training_dataset_record(manifest_path)
    audit_payload = json.loads(audit_json.read_text(encoding="utf-8"))
    assert "routing_and_label_upgrade_readiness" in audit_payload
    md_text = audit_md.read_text(encoding="utf-8")
    assert "Routing and Label Upgrade Readiness" in md_text
