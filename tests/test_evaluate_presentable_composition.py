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


def test_evaluate_presentable_produces_critique(tmp_path: Path, monkeypatch) -> None:
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
    payload = analyzer.evaluate_presentable()
    assert isinstance(payload["does_it_realize_the_brief"], bool)
    assert len(payload["where_it_betrays_the_brief"]) >= 1
    assert "engineering_diagnostics" in payload
    assert "presentability_score" in payload["engineering_diagnostics"]
