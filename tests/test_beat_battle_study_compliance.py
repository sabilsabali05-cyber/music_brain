from __future__ import annotations

import json
from pathlib import Path

from features.beat_battle_agent.battle_result_memory import ingest_local_battle_result
from features.beat_battle_agent.compliance_policy import assert_live_automation_allowed, build_compliance_snapshot
from features.beat_battle_agent.manual_round_import import import_manual_round
from features.beat_battle_agent.round_beat_generator import generate_round_beats
from features.beat_battle_agent.synplant_study_catalog import generate_synplant_study_catalog
from scripts.train_battle_outcome_ranker import build_training_report


def _write_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _write_agent_config(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "beat_battle_agent.local.json").write_text(json.dumps({}), encoding="utf-8")


def test_no_auto_submit_path_enabled() -> None:
    snapshot = build_compliance_snapshot(Path(".").resolve())
    assert snapshot["auto_submit_enabled"] is False
    assert snapshot["manual_submission_required"] is True


def test_live_browser_automation_blocked_without_authorization(tmp_path: Path) -> None:
    allowed, blocker = assert_live_automation_allowed(tmp_path)
    assert allowed is False
    assert blocker != ""


def test_manual_import_redacts_local_paths_and_ignores_raw_commit(tmp_path: Path) -> None:
    sounds_dir = tmp_path / "local_round" / "sounds"
    _write_file(sounds_dir / "kick.wav", b"kick")
    _write_file(sounds_dir / "snare.wav", b"snare")
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "beat_battle_manual_round.local.json").write_text(
        json.dumps({"round_id": "R100", "round_sounds_folder": sounds_dir.as_posix()}),
        encoding="utf-8",
    )
    result = import_manual_round(tmp_path)
    assert result["ok"] is True
    manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["source_folder"] == "<REDACTED_LOCAL_FOLDER>"
    assert all(row["source_path"] == "<REDACTED_LOCAL_PATH>" for row in manifest["sounds"])
    assert all(row["submission_allowed"] is True for row in manifest["sounds"])
    assert not list((tmp_path / "datasets" / "beat_battle_agent").rglob("*.wav"))


def test_synplant_study_rows_not_submission_allowed(tmp_path: Path) -> None:
    sounds_dir = tmp_path / "local_round" / "sounds"
    _write_file(sounds_dir / "tone.wav", b"tone")
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "beat_battle_manual_round.local.json").write_text(
        json.dumps({"round_id": "R200", "round_sounds_folder": sounds_dir.as_posix()}),
        encoding="utf-8",
    )
    import_result = import_manual_round(tmp_path)
    assert import_result["ok"] is True
    catalog_result = generate_synplant_study_catalog(tmp_path)
    assert catalog_result["ok"] is True
    catalog_path = tmp_path / "datasets" / "beat_battle_agent" / "synplant_study_catalog.jsonl"
    rows = [json.loads(line) for line in catalog_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows
    assert all(row["submission_allowed"] is False for row in rows)
    assert all(row["study_allowed"] is True for row in rows)


def test_submission_pack_excludes_synplant(tmp_path: Path) -> None:
    _write_agent_config(tmp_path)
    sounds_dir = tmp_path / "local_round" / "sounds"
    for index in range(8):
        _write_file(sounds_dir / f"snd{index}.wav", f"wav{index}".encode("utf-8"))
    (tmp_path / "config" / "beat_battle_manual_round.local.json").write_text(
        json.dumps({"round_id": "R300", "round_sounds_folder": sounds_dir.as_posix()}),
        encoding="utf-8",
    )
    import_result = import_manual_round(tmp_path)
    assert import_result["ok"] is True

    from features.beat_battle_agent.agent_config_schema import load_agent_config

    config = load_agent_config(tmp_path / "config" / "beat_battle_agent.local.json")
    result = generate_round_beats(tmp_path, config, "R300")
    assert result["blocker"] == ""
    pack = json.loads(Path(result["submission_pack_path"]).read_text(encoding="utf-8"))
    assert pack["synplant_included"] is False


def test_result_ingestion_creates_learning_rows(tmp_path: Path) -> None:
    local_result = tmp_path / "reports" / "review_queue" / "beat_battle_result.local.json"
    local_result.parent.mkdir(parents=True, exist_ok=True)
    local_result.write_text(
        json.dumps({"round_id": "R400", "draft_id": "R400_submission_01", "placement": 2, "score": 96.5, "outcome": "top3"}),
        encoding="utf-8",
    )
    result = ingest_local_battle_result(tmp_path)
    assert result["ok"] is True
    battle_rows = (tmp_path / "datasets" / "beat_battle_agent" / "battle_results.jsonl").read_text(encoding="utf-8").splitlines()
    feedback_rows = (tmp_path / "datasets" / "taste_learning" / "beat_battle_site_feedback.jsonl").read_text(encoding="utf-8").splitlines()
    assert len([line for line in battle_rows if line.strip()]) == 1
    assert len([line for line in feedback_rows if line.strip()]) == 1


def test_under_20_results_uses_heuristic_baseline() -> None:
    payload = build_training_report(19)
    assert payload["training_mode"] == "heuristic_baseline"


def test_no_fake_results_allowed(tmp_path: Path) -> None:
    payload = {"round_id": "R500", "draft_id": "R500_submission_01", "fake_result": True}
    (tmp_path / "reports" / "review_queue").mkdir(parents=True, exist_ok=True)
    (tmp_path / "reports" / "review_queue" / "beat_battle_result.local.json").write_text(json.dumps(payload), encoding="utf-8")
    result = ingest_local_battle_result(tmp_path)
    assert result["ok"] is False
    assert result["blocker"] == "fake_results_not_allowed"
