from __future__ import annotations

import json
from pathlib import Path

from scripts import (
    audit_model_witnesses,
    build_source_audio_study_manifest,
    build_source_audio_witness_consensus,
    build_source_database_taste_dossier,
    build_source_understood_composition,
    evaluate_source_understood_composition,
    run_source_audio_model_witnesses,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def _patch_source_audio_manifest_paths(monkeypatch, root: Path) -> None:
    monkeypatch.setattr(build_source_audio_study_manifest, "ROOT_DIR", root)
    monkeypatch.setattr(build_source_audio_study_manifest, "OUT_DIR", root / "datasets" / "source_audio_study")
    monkeypatch.setattr(
        build_source_audio_study_manifest,
        "OUT_JSONL",
        build_source_audio_study_manifest.OUT_DIR / "source_audio_study_manifest.jsonl",
    )
    monkeypatch.setattr(build_source_audio_study_manifest, "REPORT_DIR", root / "reports" / "source_audio_study")
    monkeypatch.setattr(
        build_source_audio_study_manifest,
        "REPORT_JSON",
        build_source_audio_study_manifest.REPORT_DIR / "source_audio_study_manifest_report.json",
    )
    monkeypatch.setattr(
        build_source_audio_study_manifest,
        "REPORT_MD",
        build_source_audio_study_manifest.REPORT_DIR / "source_audio_study_manifest_report.md",
    )


def test_unavailable_witnesses_reported_honestly(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(audit_model_witnesses, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(audit_model_witnesses, "REPORT_DIR", tmp_path / "reports" / "model_witnesses")
    monkeypatch.setattr(audit_model_witnesses, "REPORT_JSON", audit_model_witnesses.REPORT_DIR / "model_witness_audit.json")
    monkeypatch.setattr(audit_model_witnesses, "REPORT_MD", audit_model_witnesses.REPORT_DIR / "model_witness_audit.md")
    audit = audit_model_witnesses.build_model_witness_audit().to_dict()
    by_id = {row["witness_id"]: row for row in audit["witnesses"]}
    assert by_id["moonbeam"]["available"] is False
    assert by_id["musicbert"]["available"] is False
    assert by_id["midigpt"]["available"] is False
    assert by_id["text2midi"]["available"] is False


def test_unauthorized_audio_is_skipped(monkeypatch, tmp_path: Path) -> None:
    manifest = [
        {
            "item_id": "a1",
            "analysis_allowed": False,
            "source_audio_ref_redacted": "<PRIVATE_LOCAL_PATH>/a1.wav",
            "provenance": {},
        }
    ]
    _write_jsonl(tmp_path / "datasets" / "source_audio_study" / "source_audio_study_manifest.jsonl", manifest)
    _write_json(
        tmp_path / "reports" / "model_witnesses" / "model_witness_audit.json",
        {"witnesses": [{"witness_id": "musicbert", "available": False}]},
    )
    monkeypatch.setattr(run_source_audio_model_witnesses, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(run_source_audio_model_witnesses, "MANIFEST_PATH", tmp_path / "datasets" / "source_audio_study" / "source_audio_study_manifest.jsonl")
    monkeypatch.setattr(run_source_audio_model_witnesses, "AUDIT_PATH", tmp_path / "reports" / "model_witnesses" / "model_witness_audit.json")
    monkeypatch.setattr(run_source_audio_model_witnesses, "OUT_DIR", tmp_path / "datasets" / "model_witnesses")
    monkeypatch.setattr(run_source_audio_model_witnesses, "OUT_JSONL", run_source_audio_model_witnesses.OUT_DIR / "source_audio_witness_observations.jsonl")
    monkeypatch.setattr(run_source_audio_model_witnesses, "REPORT_DIR", tmp_path / "reports" / "model_witnesses")
    monkeypatch.setattr(run_source_audio_model_witnesses, "REPORT_JSON", run_source_audio_model_witnesses.REPORT_DIR / "source_audio_witness_run_report.json")
    monkeypatch.setattr(run_source_audio_model_witnesses, "REPORT_MD", run_source_audio_model_witnesses.REPORT_DIR / "source_audio_witness_run_report.md")
    observations, report = run_source_audio_model_witnesses.build_observations()
    assert observations == []
    assert report["skipped_unauthorized_count"] == 1
    assert report["witness_observations_created"] == 0


def test_observations_need_backend_or_heuristic_label(monkeypatch, tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "datasets" / "source_audio_study" / "source_audio_study_manifest.jsonl",
        [
            {
                "item_id": "x1",
                "analysis_allowed": True,
                "source_audio_ref_redacted": "<PRIVATE_LOCAL_PATH>/x1.wav",
                "provenance": {},
            }
        ],
    )
    _write_json(tmp_path / "reports" / "model_witnesses" / "model_witness_audit.json", {"witnesses": []})
    monkeypatch.setattr(run_source_audio_model_witnesses, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(run_source_audio_model_witnesses, "MANIFEST_PATH", tmp_path / "datasets" / "source_audio_study" / "source_audio_study_manifest.jsonl")
    monkeypatch.setattr(run_source_audio_model_witnesses, "AUDIT_PATH", tmp_path / "reports" / "model_witnesses" / "model_witness_audit.json")
    observations, _ = run_source_audio_model_witnesses.build_observations()
    for row in observations:
        if row["used_real_backend"] is False:
            assert row["heuristic_witness_label"] != ""


def test_consensus_includes_disagreement(monkeypatch, tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "datasets" / "model_witnesses" / "source_audio_witness_observations.jsonl",
        [
            {"item_id": "i1", "witness_id": "heuristic_local_features", "backend_status": "heuristic", "heuristic_witness_label": "heuristic_local_features"},
            {"item_id": "i1", "witness_id": "musicbert", "backend_status": "unavailable", "heuristic_witness_label": "backend_unavailable_skip"},
        ],
    )
    monkeypatch.setattr(build_source_audio_witness_consensus, "OBS_PATH", tmp_path / "datasets" / "model_witnesses" / "source_audio_witness_observations.jsonl")
    rows, report = build_source_audio_witness_consensus.build_consensus()
    assert report["items_with_disagreement"] == 1
    assert rows[0]["disagreements"]


def test_dossier_is_principles_over_averages(monkeypatch, tmp_path: Path) -> None:
    _write_jsonl(tmp_path / "datasets" / "model_witnesses" / "source_audio_witness_consensus.jsonl", [{"item_id": "i1", "consensus_id": "c1"}])
    _write_json(tmp_path / "reports" / "source_audio_study" / "source_audio_study_manifest_report.json", {"source_items_considered": 1})
    monkeypatch.setattr(build_source_database_taste_dossier, "CONSENSUS_PATH", tmp_path / "datasets" / "model_witnesses" / "source_audio_witness_consensus.jsonl")
    monkeypatch.setattr(build_source_database_taste_dossier, "MANIFEST_REPORT", tmp_path / "reports" / "source_audio_study" / "source_audio_study_manifest_report.json")
    dossier, _ = build_source_database_taste_dossier.build_dossier()
    assert dossier.strongest_principles
    assert "score-first" in " ".join(dossier.rejected_principles).lower()


def test_brief_cites_source_db_principles(monkeypatch, tmp_path: Path) -> None:
    _write_json(tmp_path / "reports" / "source_taste_understanding" / "source_database_taste_dossier.json", {"rejected_principles": [], "witness_influence_summary": [], "weak_evidence_limits": []})
    _write_jsonl(
        tmp_path / "datasets" / "source_taste_understanding" / "source_database_generative_principles.jsonl",
        [{"principle_id": "p1", "statement": "Transform, do not copy."}],
    )
    monkeypatch.setattr(build_source_database_taste_dossier, "ROOT_DIR", tmp_path)
    from scripts import build_drawing_board_composition_brief as drawing_board

    monkeypatch.setattr(drawing_board, "ROOT_DIR", tmp_path)
    brief = drawing_board.build_brief()
    assert brief["source_db_principles"]


def test_path_redaction_in_source_audio_manifest(tmp_path: Path) -> None:
    trust = tmp_path / "features" / "performances" / "p" / "s" / "trust" / "training_data_audit.json"
    _write_json(
        trust,
        {
            "performance_id": "p",
            "artifacts": {"source_audio_reference": "C:/Users/private/source.wav"},
            "authorization_status": "unknown",
            "analysis_allowed": False,
        },
    )
    payload = json.loads(trust.read_text(encoding="utf-8"))
    item = build_source_audio_study_manifest._build_item(trust, payload, [], None)
    assert "C:/Users/" not in item.source_audio_ref_redacted


def test_windows_path_matching_handles_slash_case_and_prefix() -> None:
    root = build_source_audio_study_manifest._root_spec(Path("C:/Users/IZZYO/OneDrive/Desktop/sounds"))
    matched, matched_root, reason = build_source_audio_study_manifest._match_root(
        r"c:\users\izzyo\OneDrive\Desktop\sounds\set1\clip.mp3",
        [root],
    )
    assert matched is True
    assert matched_root is not None
    assert reason == "root_folder_prefix_match"


def test_file_root_matching_requires_exact_match() -> None:
    file_root = build_source_audio_study_manifest._root_spec(Path("C:/Users/izzyo/OneDrive/Desktop/sounds/clip.wav"))
    matched, _, _ = build_source_audio_study_manifest._match_root(
        r"C:\Users\izzyo\OneDrive\Desktop\sounds\clip.wav",
        [file_root],
    )
    not_matched, _, _ = build_source_audio_study_manifest._match_root(
        r"C:\Users\izzyo\OneDrive\Desktop\sounds\clip.wav\child.wav",
        [file_root],
    )
    assert matched is True
    assert not_matched is False


def test_missing_local_config_adds_manifest_blocker(monkeypatch, tmp_path: Path) -> None:
    trust = tmp_path / "features" / "performances" / "p" / "s" / "trust" / "training_data_audit.json"
    _write_json(
        trust,
        {
            "performance_id": "p",
            "artifacts": {"source_audio_reference": "D:/audio/clip.wav"},
            "analysis_allowed": True,
        },
    )
    _patch_source_audio_manifest_paths(monkeypatch, tmp_path)
    monkeypatch.setattr(
        build_source_audio_study_manifest,
        "LOCAL_AUTH_CONFIG",
        tmp_path / "config" / "source_audio_study_authorization.local.json",
    )
    items, report = build_source_audio_study_manifest.build_manifest()
    assert len(items) == 1
    assert report["analysis_allowed_count"] == 0
    assert "missing_local_authorization_config" in report["blockers"]


def test_existing_roots_without_supported_files_add_blocker(monkeypatch, tmp_path: Path) -> None:
    source_root = tmp_path / "authorized_audio"
    source_root.mkdir(parents=True, exist_ok=True)
    trust = tmp_path / "features" / "performances" / "p" / "s" / "trust" / "training_data_audit.json"
    _write_json(
        trust,
        {
            "performance_id": "p",
            "artifacts": {"source_audio_reference": str(source_root / "clip.mp3")},
            "analysis_allowed": True,
        },
    )
    local_cfg = tmp_path / "config" / "source_audio_study_authorization.local.json"
    _write_json(local_cfg, {"analysis_allowed_roots": [str(source_root)], "training_allowed_roots": []})
    _patch_source_audio_manifest_paths(monkeypatch, tmp_path)
    monkeypatch.setattr(build_source_audio_study_manifest, "LOCAL_AUTH_CONFIG", local_cfg)
    _, report = build_source_audio_study_manifest.build_manifest()
    assert report["source_items_matched_to_allowed_roots"] == 1
    assert "allowed_roots_exist_but_no_supported_files" in report["blockers"]


def test_manifest_report_roots_are_redacted(monkeypatch, tmp_path: Path) -> None:
    trust = tmp_path / "features" / "performances" / "p" / "s" / "trust" / "training_data_audit.json"
    _write_json(
        trust,
        {
            "performance_id": "p",
            "artifacts": {"source_audio_reference": "C:/Users/private/audio/clip.mp3"},
            "analysis_allowed": True,
        },
    )
    local_cfg = tmp_path / "config" / "source_audio_study_authorization.local.json"
    _write_json(local_cfg, {"analysis_allowed_roots": ["C:/Users/private/audio"], "training_allowed_roots": []})
    _patch_source_audio_manifest_paths(monkeypatch, tmp_path)
    monkeypatch.setattr(build_source_audio_study_manifest, "LOCAL_AUTH_CONFIG", local_cfg)
    _, report = build_source_audio_study_manifest.build_manifest()
    report_text = json.dumps(report)
    assert "C:/Users/" not in report_text
    assert "<PRIVATE_LOCAL_PATH>" in report_text


def test_local_authorization_config_is_gitignored() -> None:
    gitignore = Path(__file__).resolve().parents[1] / ".gitignore"
    text = gitignore.read_text(encoding="utf-8")
    assert "config/source_audio_study_authorization.local.json" in text


def test_fixture_draft_not_usable_as_real_draft(tmp_path: Path) -> None:
    fixture = tmp_path / "outputs" / "presentable_composition_from_draft_v1" / "fixture.mid"
    fixture.parent.mkdir(parents=True, exist_ok=True)
    fixture.write_text("not-midi", encoding="utf-8")
    passed, reason = build_source_understood_composition._midi_gate_passed(fixture)
    assert passed is False
    assert reason == "fixture_draft_not_allowed"


def test_evaluation_is_critique_first_not_score_first(monkeypatch, tmp_path: Path) -> None:
    _write_json(
        tmp_path / "outputs" / "source_understood_composition_v1" / "source_understood_composition_summary.json",
        {"source_understood_composition_generated": True, "draft_real_midi_gate_passed": True, "source_db_principles_cited": ["p1"]},
    )
    monkeypatch.setattr(evaluate_source_understood_composition, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(evaluate_source_understood_composition, "SUMMARY_PATH", tmp_path / "outputs" / "source_understood_composition_v1" / "source_understood_composition_summary.json")
    monkeypatch.setattr(evaluate_source_understood_composition, "REPORT_DIR", tmp_path / "reports" / "source_understood_composition")
    monkeypatch.setattr(evaluate_source_understood_composition, "REPORT_JSON", evaluate_source_understood_composition.REPORT_DIR / "source_understood_composition_eval.json")
    monkeypatch.setattr(evaluate_source_understood_composition, "REPORT_MD", evaluate_source_understood_composition.REPORT_DIR / "source_understood_composition_eval.md")
    _ = evaluate_source_understood_composition.main()
    payload = json.loads(evaluate_source_understood_composition.REPORT_JSON.read_text(encoding="utf-8"))
    assert "critique_first_summary" in payload
    assert "engineering_diagnostics" in payload
    assert "score" not in payload
