from __future__ import annotations

import json
from pathlib import Path

from features.composition_projects import midi_draft_analyzer as analyzer
from tests._presentable_test_utils import build_test_midi, write_local_config


def _patch(monkeypatch, root: Path) -> None:
    monkeypatch.setattr(analyzer, "ROOT_DIR", root)
    monkeypatch.setattr(analyzer, "OUTPUT_ROOT", root / "outputs" / analyzer.PROJECT_ID)
    monkeypatch.setattr(analyzer, "REPORTS_ROOT", root / "reports" / "composition_projects")
    monkeypatch.setattr(analyzer, "DATASET_ROOT", root / "datasets" / "composition_projects")
    monkeypatch.setattr(analyzer, "DEFAULT_LOCAL_CONFIG", root / "config" / "presentable_composition_from_draft.local.json")


def test_generate_candidates_creates_full_and_stems(tmp_path: Path, monkeypatch) -> None:
    midi_path = tmp_path / "input" / "draft.mid"
    build_test_midi(midi_path)
    write_local_config(tmp_path, midi_path, candidate_count=8)
    _patch(monkeypatch, tmp_path)
    context = analyzer.load_context()
    analysis = analyzer.analyze_draft(context)
    comparison = analyzer.compare_draft_to_database(analysis)
    spec = analyzer.build_composition_control_spec(analysis, comparison, context)
    report = analyzer.generate_candidates(spec, context)
    assert int(report["candidates_generated"]) >= 8
    c1 = tmp_path / "outputs" / analyzer.PROJECT_ID / "candidates" / "candidate_01"
    assert (c1 / "full.mid").exists()
    assert (c1 / "stems" / "bass.mid").exists()
    features = json.loads((c1 / "candidate_features.json").read_text(encoding="utf-8"))
    assert 0.0 <= float(features["presentability_score"]) <= 1.0
