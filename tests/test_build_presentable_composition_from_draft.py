from __future__ import annotations

import json
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


def test_full_pipeline_writes_summary_and_redacts(tmp_path: Path, monkeypatch) -> None:
    midi_path = tmp_path / "input" / "draft.mid"
    build_test_midi(midi_path)
    write_local_config(tmp_path, midi_path, training_allowed=False, candidate_count=8)
    _patch(monkeypatch, tmp_path)
    summary = analyzer.run_full_pipeline(include_reaper=True)
    assert summary["status"] == "ok"
    assert int(summary["candidates_generated"]) >= 8
    assert summary["selected_candidate"].startswith("candidate_")
    assert "C:/Users/" not in json.dumps(summary)
    assert summary["draft_understanding_dossier_path"].endswith("jaca_draft_musical_understanding.json")
    assert summary["final_critique_path"].endswith("presentable_composition_eval.json")
    assert (tmp_path / "reports" / "composition_projects" / "presentable_composition_eval.json").exists()


def test_full_pipeline_handles_missing_midi(tmp_path: Path, monkeypatch) -> None:
    cfg = tmp_path / "config" / "presentable_composition_from_draft.local.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(
        '{"local_input_midi_path":"C:/Users/hidden/missing.mid","training_allowed":false,"candidate_count":8}\n',
        encoding="utf-8",
    )
    _patch(monkeypatch, tmp_path)
    summary = analyzer.run_full_pipeline(include_reaper=False)
    assert summary["status"] == analyzer.INPUT_PATH_REQUIRED_STATUS
