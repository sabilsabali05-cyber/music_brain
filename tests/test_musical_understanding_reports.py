from __future__ import annotations

import json
from pathlib import Path

from mido import MetaMessage, MidiFile, MidiTrack

from features.composition_projects import midi_draft_analyzer as analyzer
from tests._presentable_test_utils import build_test_midi, write_local_config


def _patch(monkeypatch, root: Path) -> None:
    monkeypatch.setattr(analyzer, "ROOT_DIR", root)
    monkeypatch.setattr(analyzer, "OUTPUT_ROOT", root / "outputs" / analyzer.PROJECT_ID)
    monkeypatch.setattr(analyzer, "REPORTS_ROOT", root / "reports" / "composition_projects")
    monkeypatch.setattr(analyzer, "DATABASE_REPORTS_ROOT", root / "reports" / "database_musicality")
    monkeypatch.setattr(analyzer, "DATASET_ROOT", root / "datasets" / "composition_projects")
    monkeypatch.setattr(analyzer, "DEFAULT_LOCAL_CONFIG", root / "config" / "presentable_composition_from_draft.local.json")


def _build_empty_midi(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    midi = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    midi.tracks.append(track)
    track.append(MetaMessage("set_tempo", tempo=500000, time=0))
    track.append(MetaMessage("end_of_track", time=0))
    midi.save(path.as_posix())


def test_understanding_reports_lead_with_qualitative_sections(tmp_path: Path, monkeypatch) -> None:
    midi_path = tmp_path / "input" / "draft.mid"
    build_test_midi(midi_path)
    write_local_config(tmp_path, midi_path)
    _patch(monkeypatch, tmp_path)
    context = analyzer.load_context()
    dossier = analyzer.analyze_draft(context)
    outputs = analyzer.write_draft_analysis_outputs(dossier)
    payload = json.loads(outputs["json"].read_text(encoding="utf-8"))
    assert "heard_evidence_summary" in payload
    assert "musicality_score" not in payload
    md = outputs["md"].read_text(encoding="utf-8")
    assert "## 3) Core Gestures" in md
    assert "## 16) Engineering Diagnostics (Secondary)" in md


def test_unknowns_and_empty_midi_are_honest(tmp_path: Path, monkeypatch) -> None:
    midi_path = tmp_path / "input" / "empty.mid"
    _build_empty_midi(midi_path)
    write_local_config(tmp_path, midi_path)
    _patch(monkeypatch, tmp_path)
    dossier = analyzer.analyze_draft(analyzer.load_context())
    assert dossier.missing_local_midi_draft is True
    assert any("missing" in item or "unknown" in item for item in dossier.what_is_unknown)
    assert dossier.core_gestures == []


def test_full_pipeline_contains_brief_and_critique_fields(tmp_path: Path, monkeypatch) -> None:
    midi_path = tmp_path / "input" / "draft.mid"
    build_test_midi(midi_path)
    write_local_config(tmp_path, midi_path)
    _patch(monkeypatch, tmp_path)
    summary = analyzer.run_full_pipeline(include_reaper=False)
    assert summary["composition_brief_path"].endswith("drawing_board_composition_brief.json")
    critique = json.loads((tmp_path / summary["final_critique_path"]).read_text(encoding="utf-8"))
    assert "where_it_betrays_the_brief" in critique
    assert "does_it_realize_the_brief" in critique


def test_private_paths_are_redacted_in_reports(tmp_path: Path, monkeypatch) -> None:
    cfg = tmp_path / "config" / "presentable_composition_from_draft.local.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text('{"local_input_midi_path":"C:/Users/hidden/secret.mid","training_allowed":false}\n', encoding="utf-8")
    _patch(monkeypatch, tmp_path)
    context = analyzer.load_context()
    dossier = analyzer.analyze_draft(context)
    outputs = analyzer.write_draft_analysis_outputs(dossier)
    assert "<PRIVATE_LOCAL_PATH>/" in outputs["json"].read_text(encoding="utf-8")
    assert "C:/Users/" not in outputs["md"].read_text(encoding="utf-8")
