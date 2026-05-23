from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.evaluate_mass_ingestion_readiness import build_readiness_report, evaluate_mass_ingestion_readiness


def test_readiness_report_schema_and_core_flags() -> None:
    report = build_readiness_report()
    payload = report.as_dict()
    assert isinstance(payload["created_at"], str)
    assert payload["ready_for_mass_ingestion"] is False
    assert payload["ready_for_controlled_batch"] is True
    assert payload["recommended_next_batch_size"] == 10


def test_controlled_batch_allowed_while_mass_ingestion_blocked() -> None:
    report = build_readiness_report().as_dict()
    assert report["ready_for_controlled_batch"] is True
    assert report["ready_for_mass_ingestion"] is False
    assert report["controlled_batch_plan"]["ready_for_controlled_batch"] is True


def test_required_readiness_gates_exist() -> None:
    gates = {item["category"]: item for item in build_readiness_report().as_dict()["gates"]}
    assert "source authorization" in gates
    assert "review burden" in gates
    assert gates["review burden"]["blocked"] is True
    assert "sample-library readiness" in gates
    assert "Synplant seed-selection readiness" in gates
    assert "Pure Data template readiness" in gates
    assert "Max/Ableton routing readiness" in gates
    assert "ratio intelligence readiness" in gates


def test_no_training_or_automation_claims() -> None:
    model_readiness = build_readiness_report().as_dict()["model_training_readiness"]
    assert model_readiness["model_training_has_happened"] is False
    assert model_readiness["synplant_automation_available"] is False
    assert model_readiness["pure_data_automation_available"] is False


def test_evaluator_writes_expected_report_outputs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "reports" / "dataset_quality").mkdir(parents=True, exist_ok=True)
    (tmp_path / "reports" / "dataset_quality" / "dataset_quality_yield_report.json").write_text(
        json.dumps({"total_generative_examples": 528, "split_review": 320}, indent=2),
        encoding="utf-8",
    )
    (tmp_path / "scripts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "scripts" / "index_sample_library.py").write_text("# placeholder", encoding="utf-8")
    (tmp_path / "features" / "texture_sound").mkdir(parents=True, exist_ok=True)
    (tmp_path / "features" / "texture_sound" / "synplant_candidate_schema.py").write_text("# placeholder", encoding="utf-8")
    (tmp_path / "features" / "texture_sound" / "composition_sound_plan_schema.py").write_text(
        "# placeholder",
        encoding="utf-8",
    )
    (tmp_path / "features" / "generative_systems").mkdir(parents=True, exist_ok=True)
    (tmp_path / "features" / "generative_systems" / "puredata_schema.py").write_text("# placeholder", encoding="utf-8")
    (tmp_path / "features" / "ratio_intelligence").mkdir(parents=True, exist_ok=True)
    (tmp_path / "features" / "ratio_intelligence" / "ratio_schema.py").write_text("# placeholder", encoding="utf-8")

    import scripts.evaluate_mass_ingestion_readiness as evaluator

    monkeypatch.setattr(evaluator, "ROOT_DIR", tmp_path)
    json_path, md_path, payload = evaluator.evaluate_mass_ingestion_readiness()

    assert json_path.exists()
    assert md_path.exists()
    assert payload["ready_for_mass_ingestion"] is False
    assert payload["ready_for_controlled_batch"] is True
    assert payload["recommended_next_batch_size"] == 10


def test_local_sample_artifacts_and_config_are_ignored_by_git() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    paths = [
        "datasets/sample_libraries/local_sounds_desktop/sample_seed_records.jsonl",
        "datasets/sample_libraries/local_sounds_desktop/sample_library_manifest.json",
        "reports/sample_libraries/local_sounds_desktop_index_report.json",
        "reports/sample_libraries/local_sounds_desktop_index_report.md",
        "config/sample_libraries/local_sounds_library.json",
    ]
    for path in paths:
        result = subprocess.run(
            ["git", "check-ignore", path],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"path should be ignored: {path}"
