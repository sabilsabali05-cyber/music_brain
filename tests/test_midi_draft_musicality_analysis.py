from __future__ import annotations

import json
from pathlib import Path

from features.composition_projects import midi_draft_analyzer as analyzer
from tests._presentable_test_utils import build_test_midi, write_local_config


def _patch_paths(monkeypatch, root: Path) -> None:
    monkeypatch.setattr(analyzer, "ROOT_DIR", root)
    monkeypatch.setattr(analyzer, "OUTPUT_ROOT", root / "outputs" / analyzer.PROJECT_ID)
    monkeypatch.setattr(analyzer, "REPORTS_ROOT", root / "reports" / "composition_projects")
    monkeypatch.setattr(analyzer, "DATABASE_REPORTS_ROOT", root / "reports" / "database_musicality")
    monkeypatch.setattr(analyzer, "DATASET_ROOT", root / "datasets" / "composition_projects")
    monkeypatch.setattr(analyzer, "DEFAULT_LOCAL_CONFIG", root / "config" / "presentable_composition_from_draft.local.json")


def test_analyze_midi_draft_outputs_and_redaction(tmp_path: Path, monkeypatch) -> None:
    midi_path = tmp_path / "input" / "draft.mid"
    build_test_midi(midi_path)
    write_local_config(tmp_path, midi_path)
    _patch_paths(monkeypatch, tmp_path)

    context = analyzer.load_context()
    analyzer.write_local_manifest(context)
    analysis = analyzer.analyze_draft(context)
    outputs = analyzer.write_draft_analysis_outputs(analysis)

    assert analysis.missing_local_midi_draft is False
    assert analysis.training_allowed is False
    assert len(analysis.core_gestures) >= 1
    assert len(analysis.generative_principles) >= 1
    payload = json.loads(outputs["json"].read_text(encoding="utf-8"))
    assert "heard_evidence_summary" in payload
    assert "engineering_diagnostics" in payload
    assert "musicality_score" not in payload
    md = outputs["md"].read_text(encoding="utf-8")
    assert "## 1) Evidence Integrity" in md
    assert "## 16) Engineering Diagnostics (Secondary)" in md
    assert "C:/Users/" not in md
    assert outputs["record"].exists()


def test_analyze_midi_draft_missing_input_safe(tmp_path: Path, monkeypatch) -> None:
    cfg = tmp_path / "config" / "presentable_composition_from_draft.local.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text('{"local_input_midi_path":"C:/Users/test/missing.mid","training_allowed":false}\n', encoding="utf-8")
    _patch_paths(monkeypatch, tmp_path)
    context = analyzer.load_context()
    analysis = analyzer.analyze_draft(context)
    assert analysis.missing_local_midi_draft is True
    assert analyzer.INPUT_PATH_REQUIRED_STATUS in analysis.what_is_unknown
    assert analysis.core_gestures == []
