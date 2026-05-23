from __future__ import annotations

import json
from pathlib import Path

from features.mass_ingestion.source_authorization_schema import validate_source_authorization
from features.texture_sound.synplant_session_log_schema import validate_synplant_session_log
from scripts.build_mass_ingestion_readiness_artifacts import build_all
from scripts.plan_historical_path_scrub import build_historical_scrub_plan
from scripts.run_controlled_ingestion_batch import write_run_report


def test_source_authorization_blocks_splice_training() -> None:
    payload = {
        "song_files": [
            {"source": "splice_pack", "training_allowed": True, "authorized": True},
        ],
        "sample_library_filters": [],
    }
    result = validate_source_authorization(payload)
    assert result.status == "invalid"
    assert any("Splice" in error for error in result.errors)


def test_synplant_session_schema_validation() -> None:
    valid, errors = validate_synplant_session_log(
        {
            "session_id": "s1",
            "patch_name": "warm_pad",
            "rating": 4,
        }
    )
    assert valid is True
    assert errors == []


def test_historical_scrub_plan_finds_paths_in_dry_run(tmp_path: Path, monkeypatch) -> None:
    tracked = tmp_path / "README.md"
    tracked.write_text("bad path C:/Users/local/music/file.wav", encoding="utf-8")

    import scripts.plan_historical_path_scrub as scrub

    monkeypatch.setattr(scrub, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(scrub, "_tracked_files", lambda: [tracked])
    payload = build_historical_scrub_plan(apply_safe=False)
    assert payload["status"] == "dry_run_ready"
    assert payload["finding_count"] == 1


def test_controlled_runner_writes_run_state(tmp_path: Path, monkeypatch) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "batch_id": "batch_test",
                "authorization_required": True,
                "allow_modal": False,
                "allow_transcription": False,
                "allow_training_export": False,
                "max_song_files": 5,
                "max_sample_library_items": 100,
                "song_files": [],
                "sample_library_filters": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    import scripts.run_controlled_ingestion_batch as runner

    monkeypatch.setattr(runner, "REPORT_DIR", tmp_path / "reports" / "controlled_ingestion")
    _, _, payload = write_run_report(manifest_path=manifest, execute=False)
    run_state_path = runner.REPORT_DIR / "runs" / "batch_test" / "run_state.json"
    assert payload["status"] == "dry_run_success"
    assert run_state_path.exists()


def test_readiness_artifacts_builder_outputs_required_files(tmp_path: Path, monkeypatch) -> None:
    import scripts.build_mass_ingestion_readiness_artifacts as builder

    monkeypatch.setattr(builder, "ROOT_DIR", tmp_path)
    (tmp_path / "datasets" / "training_exports").mkdir(parents=True, exist_ok=True)
    outputs = build_all()
    assert "review_queue" in outputs
    assert (tmp_path / "datasets" / "review_queue" / "review_queue_v1.jsonl").exists()
    assert (tmp_path / "datasets" / "data_quality" / "training_candidate_quality_scores.jsonl").exists()
    assert (tmp_path / "datasets" / "model_training" / "symbolic_corpus_v1" / "train.jsonl").exists()
    assert (tmp_path / "reports" / "model_evaluation" / "generated_composition_scorecard.json").exists()
    assert (tmp_path / "reports" / "feedback" / "feedback_summary.json").exists()
    assert (tmp_path / "datasets" / "puredata" / "template_library_v1.json").exists()
    assert (tmp_path / "datasets" / "ableton_routing" / "routing_records_v1.jsonl").exists()
