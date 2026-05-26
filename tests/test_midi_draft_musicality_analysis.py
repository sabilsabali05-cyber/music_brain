from __future__ import annotations

import json
from pathlib import Path

from features.composition_projects import midi_draft_analyzer as analyzer
from tests._presentable_test_utils import build_test_midi, write_local_config


def _patch_paths(monkeypatch, root: Path) -> None:
    monkeypatch.setattr(analyzer, "ROOT_DIR", root)
    monkeypatch.setattr(analyzer, "OUTPUT_ROOT", root / "outputs" / analyzer.PROJECT_ID)
    monkeypatch.setattr(analyzer, "REPORTS_ROOT", root / "reports" / "composition_projects")
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
    assert len(analysis.top_strengths) == 10
    assert len(analysis.top_weaknesses) == 10
    payload = json.loads(outputs["json"].read_text(encoding="utf-8"))
    assert payload["musicality_score"] >= 0.0
    assert payload["input_source_class"] == "real_local_midi"
    assert "C:/Users/" not in outputs["md"].read_text(encoding="utf-8")
    assert "resolved_input_midi_path_redacted" in payload
    assert outputs["record"].exists()
    assert (tmp_path / "reports" / "composition_projects" / "jaca_draft_musical_understanding.json").exists()
    assert (tmp_path / "reports" / "composition_projects" / "jaca_draft_musical_understanding.md").exists()


def test_real_workflow_refuses_fixture(tmp_path: Path, monkeypatch) -> None:
    fixture = tmp_path / "validation_inputs" / "draft.mid"
    build_test_midi(fixture)
    cfg = tmp_path / "config" / "presentable_composition_from_draft.local.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(
        json.dumps({"local_input_midi_path": fixture.as_posix(), "training_allowed": False}, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    _patch_paths(monkeypatch, tmp_path)
    context = analyzer.load_context(require_local_config=True, allow_fixture_for_tests=False)
    assert context.resolution_status == analyzer.FALLBACK_FIXTURE_USED_STATUS
    assert context.local_midi_found is False


def test_missing_local_config_fails(tmp_path: Path, monkeypatch) -> None:
    _patch_paths(monkeypatch, tmp_path)
    context = analyzer.load_context(require_local_config=True)
    assert context.resolution_status == analyzer.MISSING_LOCAL_MIDI_CONFIG_STATUS
    assert context.local_midi_found is False


def test_analyze_midi_draft_missing_input_fails(tmp_path: Path, monkeypatch) -> None:
    cfg = tmp_path / "config" / "presentable_composition_from_draft.local.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text('{"local_input_midi_path":"C:/Users/test/missing.mid","training_allowed":false}\n', encoding="utf-8")
    _patch_paths(monkeypatch, tmp_path)
    context = analyzer.load_context(require_local_config=True)
    analysis = analyzer.analyze_draft(context)
    assert analysis.missing_local_midi_draft is True
    assert context.resolution_status == analyzer.INPUT_PATH_REQUIRED_STATUS
    assert context.input_source_class == "missing_local_midi"


def test_fixture_allowed_in_test_mode(tmp_path: Path, monkeypatch) -> None:
    fixture = tmp_path / "validation_inputs" / "draft.mid"
    build_test_midi(fixture)
    write_local_config(tmp_path, fixture)
    _patch_paths(monkeypatch, tmp_path)
    context = analyzer.load_context(require_local_config=True, allow_fixture_for_tests=True)
    assert context.resolution_status == analyzer.OK_STATUS
    assert context.input_source_class == "fixture_test_midi"
    assert context.local_midi_found is True


def test_audit_mode_does_not_generate_composition(tmp_path: Path, monkeypatch) -> None:
    midi_path = tmp_path / "input" / "draft.mid"
    build_test_midi(midi_path)
    write_local_config(tmp_path, midi_path)
    _patch_paths(monkeypatch, tmp_path)
    context = analyzer.load_context(require_local_config=True)
    analyzer.write_local_manifest(context)
    analysis = analyzer.analyze_draft(context)
    analyzer.write_draft_analysis_outputs(analysis)
    assert not (tmp_path / "outputs" / analyzer.PROJECT_ID / "candidates").exists()
