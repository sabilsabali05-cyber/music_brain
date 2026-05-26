from __future__ import annotations

from pathlib import Path

from features.composition_projects import midi_draft_analyzer as analyzer
from tests._presentable_test_utils import build_test_midi, write_local_config


def _patch(monkeypatch, root: Path) -> None:
    monkeypatch.setattr(analyzer, "ROOT_DIR", root)
    monkeypatch.setattr(analyzer, "OUTPUT_ROOT", root / "outputs" / analyzer.PROJECT_ID)
    monkeypatch.setattr(analyzer, "REPORTS_ROOT", root / "reports" / "composition_projects")
    monkeypatch.setattr(analyzer, "DATABASE_REPORTS_ROOT", root / "reports" / "database_musicality")
    monkeypatch.setattr(analyzer, "DATASET_ROOT", root / "datasets" / "composition_projects")
    monkeypatch.setattr(analyzer, "DEFAULT_LOCAL_CONFIG", root / "config" / "presentable_composition_from_draft.local.json")


def test_repair_selected_runs_and_updates_report(tmp_path: Path, monkeypatch) -> None:
    midi_path = tmp_path / "input" / "draft.mid"
    build_test_midi(midi_path)
    write_local_config(tmp_path, midi_path)
    _patch(monkeypatch, tmp_path)
    context = analyzer.load_context()
    analysis = analyzer.analyze_draft(context)
    comparison = analyzer.compare_draft_to_database(analysis)
    spec = analyzer.build_composition_control_spec(analysis, comparison, context)
    analyzer.generate_candidates(spec, context)
    analyzer.rank_candidates()
    repair = analyzer.repair_selected()
    assert "presentability_before" in repair
    assert "presentability_after" in repair
    assert (tmp_path / "outputs" / analyzer.PROJECT_ID / "repair_report.json").exists()
