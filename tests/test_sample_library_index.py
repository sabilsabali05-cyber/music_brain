from __future__ import annotations

import json
from pathlib import Path

from scripts.index_sample_library import index_sample_library, load_library_config


def _write_config(config_path: Path, root_path: Path) -> None:
    payload = {
        "library_id": "local_sounds_desktop",
        "root_path": str(root_path),
        "source_type": "local_sample_seed_library",
        "intended_uses": [
            "synplant_seed_selection",
            "texture_learning",
            "sound_role_retrieval",
            "future_model_training",
        ],
        "authorization_status": "user_local_claimed",
        "ingestion_policy": {
            "do_not_move_source_files": True,
            "do_not_modify_source_files": True,
            "hash_files": True,
            "include_nested_folders": True,
            "skip_unsupported_files": True,
        },
    }
    config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def test_local_sample_library_config_loads() -> None:
    config_path = Path("config/sample_libraries/local_sounds_library.example.json")
    payload = load_library_config(config_path)
    assert payload["library_id"] == "local_sounds_desktop"
    assert payload["source_type"] == "local_sample_seed_library"
    assert "synplant_seed_selection" in payload["intended_uses"]
    assert "texture_learning" in payload["intended_uses"]
    assert payload["ingestion_policy"]["do_not_move_source_files"] is True
    assert payload["ingestion_policy"]["do_not_modify_source_files"] is True


def test_index_skips_unsupported_and_preserves_source_files(tmp_path: Path, monkeypatch) -> None:
    source_root = tmp_path / "sounds"
    source_root.mkdir(parents=True, exist_ok=True)
    good = source_root / "drums" / "kick.wav"
    good.parent.mkdir(parents=True, exist_ok=True)
    good.write_bytes(b"wav-data")
    unsupported = source_root / "notes.txt"
    unsupported.write_text("not audio", encoding="utf-8")
    before_size = good.stat().st_size
    before_mtime_ns = good.stat().st_mtime_ns

    config_path = tmp_path / "local_library.json"
    _write_config(config_path, source_root)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "scripts.index_sample_library.probe_audio_metadata",
        lambda path: {"duration_seconds": 0.8, "sample_rate": 44100, "channels": 2, "format": "wav"},
    )
    result = index_sample_library(config_path)
    records = _read_jsonl(result.records_path)
    report_payload = json.loads(result.report_json_path.read_text(encoding="utf-8"))

    assert len(records) == 1
    assert report_payload["unsupported_files_skipped"] == 1
    assert report_payload["unsupported_files"][0].endswith("notes.txt")
    assert records[0]["file_hash_sha256"]
    assert records[0]["source_path"]
    assert records[0]["relative_path"] == "drums/kick.wav"
    assert records[0]["source_type"] == "local_sample_seed_library"
    assert records[0]["ingestion_context"] == "sample_library_indexing"
    assert "synplant_seed_selection" in records[0]["intended_uses"]
    assert "texture_learning" in records[0]["intended_uses"]
    assert good.exists()
    assert good.stat().st_size == before_size
    assert good.stat().st_mtime_ns == before_mtime_ns


def test_unreadable_file_does_not_crash_and_is_marked_for_review(tmp_path: Path, monkeypatch) -> None:
    source_root = tmp_path / "sounds"
    source_root.mkdir(parents=True, exist_ok=True)
    good = source_root / "lead.wav"
    bad = source_root / "broken.wav"
    good.write_bytes(b"good-data")
    bad.write_bytes(b"bad-data")

    config_path = tmp_path / "local_library.json"
    _write_config(config_path, source_root)
    monkeypatch.chdir(tmp_path)

    def _fake_hash(path: Path) -> str:
        if path.name == "broken.wav":
            raise OSError("simulated read failure")
        return "okhash"

    monkeypatch.setattr("scripts.index_sample_library.file_sha256", _fake_hash)
    monkeypatch.setattr(
        "scripts.index_sample_library.probe_audio_metadata",
        lambda path: {"duration_seconds": 0.5, "sample_rate": 44100, "channels": 1, "format": "wav"},
    )

    result = index_sample_library(config_path)
    records = _read_jsonl(result.records_path)
    report_payload = json.loads(result.report_json_path.read_text(encoding="utf-8"))
    by_name = {row["filename"]: row for row in records}

    assert len(records) == 2
    assert report_payload["unreadable_or_problem_files"] == 1
    assert "broken.wav" in by_name
    assert by_name["broken.wav"]["review_status"] == "needs_review"
    assert by_name["lead.wav"]["review_status"] == "indexed_unreviewed"


def test_mixed_asset_heuristics_and_role_dependencies(tmp_path: Path, monkeypatch) -> None:
    source_root = tmp_path / "sounds"
    source_root.mkdir(parents=True, exist_ok=True)
    drum_break = source_root / "beats" / "amen_break_loop.wav"
    synth = source_root / "synth" / "hyper_synth_hit.wav"
    unknown = source_root / "misc" / "mystery_blob.wav"
    drum_break.parent.mkdir(parents=True, exist_ok=True)
    synth.parent.mkdir(parents=True, exist_ok=True)
    unknown.parent.mkdir(parents=True, exist_ok=True)
    drum_break.write_bytes(b"a")
    synth.write_bytes(b"b")
    unknown.write_bytes(b"c")

    config_path = tmp_path / "local_library.json"
    _write_config(config_path, source_root)
    monkeypatch.chdir(tmp_path)

    def _fake_meta(path: Path) -> dict[str, object]:
        if path.name == "amen_break_loop.wav":
            return {"duration_seconds": 6.5, "sample_rate": 44100, "channels": 2, "format": "wav"}
        if path.name == "hyper_synth_hit.wav":
            return {"duration_seconds": 0.6, "sample_rate": 44100, "channels": 1, "format": "wav"}
        return {"duration_seconds": None, "sample_rate": None, "channels": None, "format": "wav"}

    monkeypatch.setattr("scripts.index_sample_library.probe_audio_metadata", _fake_meta)
    result = index_sample_library(config_path)
    records = _read_jsonl(result.records_path)
    by_name = {row["filename"]: row for row in records}

    break_record = by_name["amen_break_loop.wav"]
    synth_record = by_name["hyper_synth_hit.wav"]
    unknown_record = by_name["mystery_blob.wav"]

    break_roles = {row["role"] for row in break_record["role_candidates"]}
    synth_roles = {row["role"] for row in synth_record["role_candidates"]}
    unknown_roles = {row["role"] for row in unknown_record["role_candidates"]}

    assert break_record["asset_type_guess"] in {"drum_break", "drum_loop"}
    assert "rhythm_source" in break_roles
    assert "slicing_candidate" in break_roles
    assert "synplant_seed_candidate" not in break_roles

    assert synth_record["asset_type_guess"] == "synth_one_shot"
    assert "synplant_seed_candidate" in synth_roles
    assert unknown_record["asset_type_guess"] == "unknown"
    assert unknown_record["needs_human_review"] is True
    assert unknown_roles == {"unknown"}

    assert break_record["asset_type_is_heuristic"] is True
    assert synth_record["asset_type_is_heuristic"] is True
    assert unknown_record["asset_type_is_heuristic"] is True
    assert "classification is heuristic and not ground truth" in break_record["limitations"]
