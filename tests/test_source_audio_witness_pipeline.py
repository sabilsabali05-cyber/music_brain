from __future__ import annotations

import json
from pathlib import Path

from scripts import build_source_audio_study_manifest, run_source_audio_model_witnesses


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def _patch_manifest_paths(monkeypatch, root: Path) -> None:
    monkeypatch.setattr(build_source_audio_study_manifest, "ROOT_DIR", root)
    monkeypatch.setattr(build_source_audio_study_manifest, "LOCAL_AUTH_CONFIG", root / "config" / "source_audio_study_authorization.local.json")
    monkeypatch.setattr(build_source_audio_study_manifest, "OUT_DIR", root / "datasets" / "source_audio_study")
    monkeypatch.setattr(build_source_audio_study_manifest, "OUT_JSONL", build_source_audio_study_manifest.OUT_DIR / "source_audio_study_manifest.jsonl")
    monkeypatch.setattr(build_source_audio_study_manifest, "CONTROLLED_BATCH_JSONL", build_source_audio_study_manifest.OUT_DIR / "source_audio_controlled_batch.jsonl")
    monkeypatch.setattr(build_source_audio_study_manifest, "LOCAL_CACHE_DIR", root / "local_source_audio_study")
    monkeypatch.setattr(build_source_audio_study_manifest, "LOCAL_PATH_MAP", build_source_audio_study_manifest.LOCAL_CACHE_DIR / "source_audio_path_map.local.json")
    monkeypatch.setattr(build_source_audio_study_manifest, "REPORT_DIR", root / "reports" / "source_audio_study")
    monkeypatch.setattr(build_source_audio_study_manifest, "REPORT_JSON", build_source_audio_study_manifest.REPORT_DIR / "source_audio_study_manifest_report.json")
    monkeypatch.setattr(build_source_audio_study_manifest, "REPORT_MD", build_source_audio_study_manifest.REPORT_DIR / "source_audio_study_manifest_report.md")
    monkeypatch.setattr(build_source_audio_study_manifest, "CONTROLLED_BATCH_REPORT_JSON", build_source_audio_study_manifest.REPORT_DIR / "source_audio_controlled_batch_report.json")
    monkeypatch.setattr(build_source_audio_study_manifest, "CONTROLLED_BATCH_REPORT_MD", build_source_audio_study_manifest.REPORT_DIR / "source_audio_controlled_batch_report.md")
    monkeypatch.setattr(build_source_audio_study_manifest, "AUDIT_JSON", build_source_audio_study_manifest.REPORT_DIR / "source_audio_manifest_population_audit.json")
    monkeypatch.setattr(build_source_audio_study_manifest, "AUDIT_MD", build_source_audio_study_manifest.REPORT_DIR / "source_audio_manifest_population_audit.md")


def test_root_discovery_creates_manifest_rows(monkeypatch, tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir(parents=True)
    (allowed / "a.wav").write_bytes(b"a")
    (allowed / "b.mp3").write_bytes(b"b")
    _write_json(
        tmp_path / "config" / "source_audio_study_authorization.local.json",
        {"analysis_allowed_roots": [str(allowed)], "reference_only_roots": [], "training_allowed_roots": []},
    )
    _patch_manifest_paths(monkeypatch, tmp_path)
    rows, _, report, _, _ = build_source_audio_study_manifest.build_manifest()
    assert len(rows) == 2
    assert report["manifest_rows_created_total"] == 2


def test_controlled_batch_respects_max(monkeypatch, tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir(parents=True)
    for idx in range(5):
        (allowed / f"item_{idx}.wav").write_bytes(b"123")
    _write_json(
        tmp_path / "config" / "source_audio_study_authorization.local.json",
        {"analysis_allowed_roots": [str(allowed)], "reference_only_roots": [], "training_allowed_roots": [], "max_items_for_controlled_batch": 3},
    )
    _patch_manifest_paths(monkeypatch, tmp_path)
    _, controlled_batch, report, controlled_report, _ = build_source_audio_study_manifest.build_manifest()
    assert len(controlled_batch) == 3
    assert report["controlled_batch_size"] == 3
    assert controlled_report["controlled_batch_size"] == 3


def test_committed_manifest_uses_redacted_and_hash_only(monkeypatch, tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir(parents=True)
    (allowed / "clip.wav").write_bytes(b"x")
    _write_json(
        tmp_path / "config" / "source_audio_study_authorization.local.json",
        {"analysis_allowed_roots": [str(allowed)], "reference_only_roots": [], "training_allowed_roots": []},
    )
    _patch_manifest_paths(monkeypatch, tmp_path)
    rows, _, _, _, _ = build_source_audio_study_manifest.build_manifest()
    row = rows[0]
    assert "path_hash" in row
    assert "redacted_path" in row
    assert "absolute_path" not in row
    assert "source_audio_ref" not in row
    assert "<PRIVATE_LOCAL_PATH>" in row["redacted_path"]


def test_raw_absolute_paths_only_in_local_map(monkeypatch, tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir(parents=True)
    source = allowed / "clip.wav"
    source.write_bytes(b"abc")
    _write_json(
        tmp_path / "config" / "source_audio_study_authorization.local.json",
        {"analysis_allowed_roots": [str(allowed)], "reference_only_roots": [], "training_allowed_roots": []},
    )
    _patch_manifest_paths(monkeypatch, tmp_path)
    assert build_source_audio_study_manifest.main() == 0
    manifest_text = build_source_audio_study_manifest.OUT_JSONL.read_text(encoding="utf-8")
    map_text = build_source_audio_study_manifest.LOCAL_PATH_MAP.read_text(encoding="utf-8")
    assert str(source) not in manifest_text
    assert "\"absolute_path\"" in map_text
    assert "clip.wav" in map_text


def test_windows_root_matching_handles_slash_case_and_prefix() -> None:
    root = build_source_audio_study_manifest._root_spec(Path("C:/Users/IZZYO/OneDrive/Desktop/sounds"))
    matched, matched_root, reason = build_source_audio_study_manifest._match_root(
        r"c:\users\izzyo\OneDrive\Desktop\sounds\set1\clip.mp3",
        [root],
    )
    assert matched is True
    assert matched_root is not None
    assert reason == "root_folder_prefix_match"


def test_witnesses_use_controlled_batch_only(monkeypatch, tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "datasets" / "source_audio_study" / "source_audio_controlled_batch.jsonl",
        [{"source_id": "a1", "analysis_allowed": True, "redacted_path": "<PRIVATE_LOCAL_PATH>/a1.wav", "source_category": "analysis_allowed_root", "media_type": "audio", "extension": ".wav"}],
    )
    _write_jsonl(
        tmp_path / "datasets" / "source_audio_study" / "source_audio_study_manifest.jsonl",
        [{"source_id": "b1", "analysis_allowed": True, "redacted_path": "<PRIVATE_LOCAL_PATH>/b1.wav", "source_category": "analysis_allowed_root", "media_type": "audio", "extension": ".wav"}],
    )
    _write_json(tmp_path / "reports" / "model_witnesses" / "model_witness_audit.json", {"witnesses": []})
    monkeypatch.setattr(run_source_audio_model_witnesses, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(run_source_audio_model_witnesses, "MANIFEST_PATH", tmp_path / "datasets" / "source_audio_study" / "source_audio_controlled_batch.jsonl")
    monkeypatch.setattr(run_source_audio_model_witnesses, "AUDIT_PATH", tmp_path / "reports" / "model_witnesses" / "model_witness_audit.json")
    observations, report = run_source_audio_model_witnesses.build_observations()
    assert {row["item_id"] for row in observations} == {"a1"}
    assert report["source_items_considered"] == 1


def test_reports_do_not_include_private_paths(monkeypatch, tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir(parents=True)
    (allowed / "clip.wav").write_bytes(b"x")
    _write_json(
        tmp_path / "config" / "source_audio_study_authorization.local.json",
        {"analysis_allowed_roots": [str(allowed)], "reference_only_roots": [], "training_allowed_roots": []},
    )
    _patch_manifest_paths(monkeypatch, tmp_path)
    assert build_source_audio_study_manifest.main() == 0
    report_text = build_source_audio_study_manifest.REPORT_JSON.read_text(encoding="utf-8")
    assert str(allowed) not in report_text
    assert "<PRIVATE_LOCAL_PATH>" in report_text


def test_missing_local_auth_config_blocks(monkeypatch, tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir(parents=True)
    (allowed / "clip.wav").write_bytes(b"x")
    _patch_manifest_paths(monkeypatch, tmp_path)
    rows, _, report, _, _ = build_source_audio_study_manifest.build_manifest()
    assert rows == []
    assert "missing_local_authorization_config" in report["blockers"]


def test_allowed_roots_with_files_have_analysis_allowed(monkeypatch, tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir(parents=True)
    (allowed / "clip.wav").write_bytes(b"x")
    _write_json(
        tmp_path / "config" / "source_audio_study_authorization.local.json",
        {"analysis_allowed_roots": [str(allowed)], "reference_only_roots": [], "training_allowed_roots": []},
    )
    _patch_manifest_paths(monkeypatch, tmp_path)
    _, _, report, controlled_report, _ = build_source_audio_study_manifest.build_manifest()
    assert report["analysis_allowed_count"] > 0
    assert controlled_report["analysis_allowed_count"] > 0


def test_local_authorization_config_and_local_map_are_gitignored() -> None:
    gitignore = Path(__file__).resolve().parents[1] / ".gitignore"
    text = gitignore.read_text(encoding="utf-8")
    assert "config/source_audio_study_authorization.local.json" in text
    assert "local_source_audio_study/" in text
