from __future__ import annotations

import json
from pathlib import Path

from features.trust.failure_taxonomy import make_failure_record
from features.trust.field_trust_policy import classify_record_for_export
from scripts.summarize_training_exports import summarize_training_exports


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_source_package_imports_still_work() -> None:
    # Smoke-import a few source modules that must remain in the source package.
    import features.rhythm_lexicon as rhythm_lexicon
    import features.rhythm_lexicon_config as rhythm_lexicon_config

    assert hasattr(rhythm_lexicon, "classify_rhythm_pattern")
    assert hasattr(rhythm_lexicon_config, "DEFAULT_LEXICON_THRESHOLD")
    assert callable(make_failure_record)
    assert callable(classify_record_for_export)


def test_summarize_training_exports_writes_summary_files(tmp_path: Path) -> None:
    root = tmp_path / "datasets" / "training_exports"
    run_a = root / "perf_a" / "run_1"
    run_b = root / "perf_b" / "run_2"
    _write_json(
        run_a / "export_manifest.json",
        {
            "performance_id": "perf_a",
            "source_feature_pack_path": (tmp_path / "features" / "performances" / "perf_a" / "run_1").as_posix(),
            "source_ai_record_count": 100,
            "accepted_observation_count": 25,
            "weak_label_count": 80,
            "audio_midi_only_count": 0,
            "review_required_count": 70,
            "quarantined_count": 0,
            "limitations": ["heuristic split"],
        },
    )
    _write_json(
        run_b / "export_manifest.json",
        {
            "performance_id": "perf_b",
            "source_feature_pack_path": (tmp_path / "features" / "performances" / "perf_b" / "run_2").as_posix(),
            "source_ai_record_count": 40,
            "accepted_observation_count": 0,
            "weak_label_count": 39,
            "audio_midi_only_count": 0,
            "review_required_count": 38,
            "quarantined_count": 2,
            "limitations": ["heuristic split", "needs review"],
            "warnings": ["downranked by quality gate"],
        },
    )
    _write_json(
        tmp_path / "features" / "performances" / "perf_a" / "run_1" / "trust" / "training_data_audit.json",
        {"dataset_inclusion_decision": "accepted"},
    )
    _write_json(
        tmp_path / "features" / "performances" / "perf_b" / "run_2" / "trust" / "training_data_audit.json",
        {"dataset_inclusion_decision": "review_required"},
    )

    summary_json, summary_md = summarize_training_exports(root)
    assert summary_json.exists()
    assert summary_md.exists()

    payload = json.loads(summary_json.read_text(encoding="utf-8"))
    assert payload["total_performances"] == 2
    assert payload["total_source_ai_records"] == 140
    assert payload["total_accepted_observation_records"] == 25
    assert payload["total_weak_label_records"] == 119
    assert payload["total_review_required_records"] == 108
    assert payload["total_quarantined_records"] == 2
    assert "perf_b" in payload["performances_with_zero_accepted_records"]
    assert "perf_b" in payload["performances_with_quarantined_records"]
    assert payload["performances_by_dataset_inclusion_decision"]["accepted"] == 1
    assert payload["performances_by_dataset_inclusion_decision"]["review_required"] == 1
