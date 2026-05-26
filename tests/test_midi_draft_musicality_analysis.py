from __future__ import annotations

import json
from pathlib import Path

from mido import Message, MetaMessage, MidiFile, MidiTrack

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
    assert "C:/Users/" not in outputs["md"].read_text(encoding="utf-8")
    assert outputs["record"].exists()


def test_analyze_midi_draft_missing_input_safe(tmp_path: Path, monkeypatch) -> None:
    cfg = tmp_path / "config" / "presentable_composition_from_draft.local.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text('{"local_input_midi_path":"C:/Users/test/missing.mid","training_allowed":false}\n', encoding="utf-8")
    _patch_paths(monkeypatch, tmp_path)
    context = analyzer.load_context()
    analysis = analyzer.analyze_draft(context)
    assert analysis.missing_local_midi_draft is True
    assert analyzer.INPUT_PATH_REQUIRED_STATUS in analysis.top_weaknesses


def _build_custom_midi(path: Path, include_tempo: bool = True, zero_velocity_off: bool = False, multi_track: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    midi = MidiFile(ticks_per_beat=480)
    track_a = MidiTrack()
    midi.tracks.append(track_a)
    if include_tempo:
        track_a.append(MetaMessage("set_tempo", tempo=500000, time=0))
    track_a.append(Message("note_on", note=60, velocity=90, time=0, channel=0))
    if zero_velocity_off:
        track_a.append(Message("note_on", note=60, velocity=0, time=240, channel=0))
    else:
        track_a.append(Message("note_off", note=60, velocity=64, time=240, channel=0))
    track_a.append(Message("note_on", note=64, velocity=88, time=120, channel=0))
    track_a.append(Message("note_off", note=64, velocity=48, time=240, channel=0))
    if multi_track:
        track_b = MidiTrack()
        midi.tracks.append(track_b)
        track_b.append(Message("note_on", note=48, velocity=80, time=0, channel=1))
        track_b.append(Message("note_off", note=48, velocity=64, time=480, channel=1))
        track_b.append(Message("note_on", note=55, velocity=75, time=0, channel=1))
        track_b.append(Message("note_off", note=55, velocity=64, time=480, channel=1))
    midi.save(path.as_posix())


def test_parser_counts_note_off_with_nonzero_velocity(tmp_path: Path, monkeypatch) -> None:
    midi_path = tmp_path / "input" / "noteoff_nonzero.mid"
    _build_custom_midi(midi_path, include_tempo=True, zero_velocity_off=False, multi_track=False)
    write_local_config(tmp_path, midi_path)
    _patch_paths(monkeypatch, tmp_path)
    analysis = analyzer.analyze_draft(analyzer.load_context())
    assert analysis.note_count >= 2
    assert analysis.tempo_bpm_detected is not None


def test_zero_velocity_note_on_is_note_off(tmp_path: Path, monkeypatch) -> None:
    midi_path = tmp_path / "input" / "zero_velocity.mid"
    _build_custom_midi(midi_path, include_tempo=True, zero_velocity_off=True, multi_track=False)
    write_local_config(tmp_path, midi_path)
    _patch_paths(monkeypatch, tmp_path)
    ctx = analyzer.load_context()
    diagnostics = analyzer.write_midi_parser_diagnostics(ctx)
    payload = json.loads(diagnostics["json"].read_text(encoding="utf-8"))
    assert payload["note_on_zero_velocity"] >= 1
    assert payload["zero_velocity_note_on_handled_as_note_off"] is True


def test_multi_track_notes_counted(tmp_path: Path, monkeypatch) -> None:
    midi_path = tmp_path / "input" / "multitrack.mid"
    _build_custom_midi(midi_path, include_tempo=True, zero_velocity_off=False, multi_track=True)
    write_local_config(tmp_path, midi_path)
    _patch_paths(monkeypatch, tmp_path)
    analysis = analyzer.analyze_draft(analyzer.load_context())
    assert analysis.track_count >= 2
    assert analysis.note_count >= 4


def test_tempo_parsing_without_meta_uses_inference(tmp_path: Path, monkeypatch) -> None:
    midi_path = tmp_path / "input" / "no_tempo.mid"
    _build_custom_midi(midi_path, include_tempo=False, zero_velocity_off=False, multi_track=False)
    write_local_config(tmp_path, midi_path)
    _patch_paths(monkeypatch, tmp_path)
    analysis = analyzer.analyze_draft(analyzer.load_context())
    tempo_meta = analysis.technical_summary.get("tempo_detection", {})
    assert analysis.tempo_bpm_detected is not None
    assert "inferred" in str(tempo_meta.get("reason", "")).lower()


def test_key_inference_from_pitch_distribution(tmp_path: Path, monkeypatch) -> None:
    midi_path = tmp_path / "input" / "key_infer.mid"
    build_test_midi(midi_path)
    write_local_config(tmp_path, midi_path)
    _patch_paths(monkeypatch, tmp_path)
    analysis = analyzer.analyze_draft(analyzer.load_context())
    assert analysis.key_detected is not None
    assert " " in analysis.key_detected


def test_empty_midi_no_fake_musicality(tmp_path: Path, monkeypatch) -> None:
    midi_path = tmp_path / "input" / "empty.mid"
    midi_path.parent.mkdir(parents=True, exist_ok=True)
    MidiFile(ticks_per_beat=480).save(midi_path.as_posix())
    write_local_config(tmp_path, midi_path)
    _patch_paths(monkeypatch, tmp_path)
    analysis = analyzer.analyze_draft(analyzer.load_context())
    assert analysis.note_count == 0
    assert analysis.musicality_score == 0.0
    assert analysis.tempo_bpm_detected is None
    assert analysis.key_detected is None


def test_private_path_redaction_in_diagnostics(tmp_path: Path, monkeypatch) -> None:
    midi_path = tmp_path / "input" / "draft.mid"
    build_test_midi(midi_path)
    write_local_config(tmp_path, midi_path)
    _patch_paths(monkeypatch, tmp_path)
    ctx = analyzer.load_context()
    diagnostics = analyzer.write_midi_parser_diagnostics(ctx)
    payload = json.loads(diagnostics["json"].read_text(encoding="utf-8"))
    assert "C:/Users/" not in payload["source_path_redacted"]
