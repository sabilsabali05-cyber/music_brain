from __future__ import annotations

from pathlib import Path

from features.composition_projects import midi_draft_analyzer as analyzer
from tests._presentable_test_utils import build_test_midi, write_local_config


def _patch(monkeypatch, root: Path) -> None:
    monkeypatch.setattr(analyzer, "ROOT_DIR", root)
    monkeypatch.setattr(analyzer, "OUTPUT_ROOT", root / "outputs" / analyzer.PROJECT_ID)
    monkeypatch.setattr(analyzer, "REPORTS_ROOT", root / "reports" / "composition_projects")
    monkeypatch.setattr(analyzer, "DATASET_ROOT", root / "datasets" / "composition_projects")
    monkeypatch.setattr(analyzer, "DEFAULT_LOCAL_CONFIG", root / "config" / "presentable_composition_from_draft.local.json")


def test_build_spec_contains_policy_and_targets(tmp_path: Path, monkeypatch) -> None:
    midi_path = tmp_path / "input" / "draft.mid"
    build_test_midi(midi_path)
    write_local_config(tmp_path, midi_path, training_allowed=False)
    _patch(monkeypatch, tmp_path)
    context = analyzer.load_context()
    analysis = analyzer.analyze_draft(context)
    comparison = analyzer.compare_draft_to_database(analysis)
    spec = analyzer.build_composition_control_spec(analysis, comparison, context)
    assert spec["source_policy"]["training_allowed"] is False
    assert spec["source_policy"]["source_audio_training_performed"] is False
    assert spec["presentability_requirements"]["minimum_presentability_score"] >= 0.7
    assert len(spec["presentability_requirements"]["must_include_stems"]) >= 5
