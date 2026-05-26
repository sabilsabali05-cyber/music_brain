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


def test_compare_draft_to_database_writes_reports(tmp_path: Path, monkeypatch) -> None:
    midi_path = tmp_path / "input" / "draft.mid"
    build_test_midi(midi_path)
    write_local_config(tmp_path, midi_path)
    _patch(monkeypatch, tmp_path)
    analysis = analyzer.analyze_draft(analyzer.load_context())
    report = analyzer.compare_draft_to_database(analysis)
    assert report["status"] == "ok"
    assert 0.0 <= float(report["confidence"]) <= 1.0
    assert (tmp_path / "reports" / "database_musicality" / "database_musical_understanding.json").exists()
    assert len(report["nearest_records"]) >= 1
    assert len(report["principles_over_averages"]) >= 1
