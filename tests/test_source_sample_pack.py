from __future__ import annotations

import json
import subprocess
import wave
from pathlib import Path

from scripts import (
    build_source_song_starter_pack,
    discover_source_loop_candidates,
    export_sample_pack_to_reaper_live_bridge,
)
from scripts.check_privacy_leaks import scan_privacy_leaks


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def _write_wav(path: Path, frame_count: int = 44100) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(44100)
        wav_file.writeframes(b"\x00\x00" * frame_count)


def _patch_discovery(monkeypatch, root: Path) -> None:
    monkeypatch.setattr(discover_source_loop_candidates, "ROOT_DIR", root)
    monkeypatch.setattr(discover_source_loop_candidates, "CONFIG_PATH", root / "config" / "source_audio_sample_pack.local.json")
    monkeypatch.setattr(discover_source_loop_candidates, "CONTROLLED_BATCH_PATH", root / "datasets" / "source_audio_study" / "source_audio_controlled_batch.jsonl")
    monkeypatch.setattr(discover_source_loop_candidates, "MANIFEST_PATH", root / "datasets" / "source_audio_study" / "source_audio_study_manifest.jsonl")
    monkeypatch.setattr(discover_source_loop_candidates, "CONSENSUS_PATH", root / "datasets" / "model_witnesses" / "source_audio_witness_consensus.jsonl")
    monkeypatch.setattr(discover_source_loop_candidates, "DOSSIER_PATH", root / "reports" / "source_taste_understanding" / "source_database_taste_dossier.json")
    monkeypatch.setattr(discover_source_loop_candidates, "LOCAL_PATH_MAP", root / "local_source_audio_study" / "source_audio_path_map.local.json")
    monkeypatch.setattr(discover_source_loop_candidates, "OUT_DIR", root / "datasets" / "source_sample_pack")
    monkeypatch.setattr(discover_source_loop_candidates, "OUT_JSONL", discover_source_loop_candidates.OUT_DIR / "source_loop_candidates.jsonl")
    monkeypatch.setattr(discover_source_loop_candidates, "REPORT_DIR", root / "reports" / "source_sample_pack")
    monkeypatch.setattr(discover_source_loop_candidates, "REPORT_JSON", discover_source_loop_candidates.REPORT_DIR / "source_loop_candidate_report.json")
    monkeypatch.setattr(discover_source_loop_candidates, "REPORT_MD", discover_source_loop_candidates.REPORT_DIR / "source_loop_candidate_report.md")


def _patch_build(monkeypatch, root: Path) -> None:
    monkeypatch.setattr(build_source_song_starter_pack, "ROOT_DIR", root)
    monkeypatch.setattr(build_source_song_starter_pack, "CONFIG_PATH", root / "config" / "source_audio_sample_pack.local.json")
    monkeypatch.setattr(build_source_song_starter_pack, "LOCAL_PATH_MAP", root / "local_source_audio_study" / "source_audio_path_map.local.json")
    monkeypatch.setattr(build_source_song_starter_pack, "CANDIDATES_PATH", root / "datasets" / "source_sample_pack" / "source_loop_candidates.jsonl")
    monkeypatch.setattr(build_source_song_starter_pack, "REPORT_DIR", root / "reports" / "source_sample_pack")
    monkeypatch.setattr(build_source_song_starter_pack, "REPORT_JSON", build_source_song_starter_pack.REPORT_DIR / "source_song_starter_pack_report.json")
    monkeypatch.setattr(build_source_song_starter_pack, "REPORT_MD", build_source_song_starter_pack.REPORT_DIR / "source_song_starter_pack_report.md")
    monkeypatch.setattr(build_source_song_starter_pack, "OUTPUT_ROOT", root / "outputs" / "source_sample_packs")


def _patch_bridge(monkeypatch, root: Path) -> None:
    monkeypatch.setattr(export_sample_pack_to_reaper_live_bridge, "ROOT_DIR", root)
    monkeypatch.setattr(export_sample_pack_to_reaper_live_bridge, "OUTPUT_ROOT", root / "outputs" / "source_sample_packs")


def test_permission_separation_blocks_export_when_audio_export_disabled(monkeypatch, tmp_path: Path) -> None:
    _patch_discovery(monkeypatch, tmp_path)
    source_file = tmp_path / "allowed" / "loop_90_Cmin.wav"
    _write_wav(source_file, frame_count=44100 * 2)
    _write_json(
        tmp_path / "config" / "source_audio_sample_pack.local.json",
        {
            "analysis_allowed_roots": [str(tmp_path / "allowed")],
            "export_allowed_roots": [str(tmp_path / "allowed")],
            "sample_pack_allowed_roots": [str(tmp_path / "allowed")],
            "reference_only_roots": [],
            "max_sample_pack_source_items": 1,
            "max_loops_per_source": 1,
            "allowed_loop_lengths_bars": [2],
            "allow_audio_loop_export": False,
            "allow_reference_to_midi_starters": True,
        },
    )
    _write_jsonl(tmp_path / "datasets" / "source_audio_study" / "source_audio_controlled_batch.jsonl", [{"source_id": "s1"}])
    _write_jsonl(
        tmp_path / "datasets" / "source_audio_study" / "source_audio_study_manifest.jsonl",
        [
            {
                "source_id": "s1",
                "path_hash": "h1",
                "redacted_path": "<PRIVATE_LOCAL_PATH>/allowed/loop_90_Cmin.wav",
                "analysis_allowed": True,
            }
        ],
    )
    _write_json(tmp_path / "local_source_audio_study" / "source_audio_path_map.local.json", {"path_map": [{"path_hash": "h1", "absolute_path": str(source_file)}]})
    _write_json(tmp_path / "reports" / "source_taste_understanding" / "source_database_taste_dossier.json", {"ok": True})
    _write_jsonl(tmp_path / "datasets" / "model_witnesses" / "source_audio_witness_consensus.jsonl", [{"item_id": "s1", "agreeing_witnesses": ["heuristic_local_features"], "confidence": 0.4}])

    candidates, _ = discover_source_loop_candidates.build_candidates()
    assert len(candidates) == 1
    assert candidates[0]["analysis_allowed"] is True
    assert candidates[0]["export_allowed"] is False


def test_reference_only_sources_create_midi_and_no_audio_copy(monkeypatch, tmp_path: Path) -> None:
    _patch_build(monkeypatch, tmp_path)
    _write_json(
        tmp_path / "config" / "source_audio_sample_pack.local.json",
        {
            "allow_audio_loop_export": True,
            "allow_reference_to_midi_starters": True,
            "allowed_loop_lengths_bars": [2],
        },
    )
    _write_json(tmp_path / "local_source_audio_study" / "source_audio_path_map.local.json", {"path_map": []})
    _write_jsonl(
        tmp_path / "datasets" / "source_sample_pack" / "source_loop_candidates.jsonl",
        [
            {
                "candidate_id": "c_ref",
                "source_id": "s_ref",
                "path_hash": "h_ref",
                "role": "melody",
                "bar_length": 2,
                "start_seconds": 0.0,
                "duration_seconds": 1.2,
                "reference_only": True,
                "export_allowed": False,
            }
        ],
    )

    manifest, summary = build_source_song_starter_pack.build_pack()
    assert len(manifest["audio_loops"]) == 0
    assert len(manifest["midi_starters"]) == 1
    assert len(manifest["recipes"]) == 1
    assert summary["reference_only_audio_skipped"] == 1


def test_discovery_rows_use_redacted_path_and_hash_only(monkeypatch, tmp_path: Path) -> None:
    _patch_discovery(monkeypatch, tmp_path)
    source_file = tmp_path / "allowed" / "loop_90_Cmin.wav"
    _write_wav(source_file)
    _write_json(
        tmp_path / "config" / "source_audio_sample_pack.local.json",
        {
            "analysis_allowed_roots": [str(tmp_path / "allowed")],
            "export_allowed_roots": [str(tmp_path / "allowed")],
            "sample_pack_allowed_roots": [str(tmp_path / "allowed")],
            "reference_only_roots": [],
            "allow_audio_loop_export": False,
            "allow_reference_to_midi_starters": True,
        },
    )
    _write_jsonl(tmp_path / "datasets" / "source_audio_study" / "source_audio_controlled_batch.jsonl", [{"source_id": "s1"}])
    _write_jsonl(
        tmp_path / "datasets" / "source_audio_study" / "source_audio_study_manifest.jsonl",
        [{"source_id": "s1", "path_hash": "h1", "redacted_path": "<PRIVATE_LOCAL_PATH>/allowed/loop_90_Cmin.wav", "analysis_allowed": True}],
    )
    _write_json(tmp_path / "local_source_audio_study" / "source_audio_path_map.local.json", {"path_map": [{"path_hash": "h1", "absolute_path": str(source_file)}]})
    _write_json(tmp_path / "reports" / "source_taste_understanding" / "source_database_taste_dossier.json", {})
    _write_jsonl(tmp_path / "datasets" / "model_witnesses" / "source_audio_witness_consensus.jsonl", [])

    candidates, _ = discover_source_loop_candidates.build_candidates()
    row = candidates[0]
    assert "path_hash" in row
    assert "source_redacted_path" in row
    assert "absolute_path" not in row
    assert "<PRIVATE_LOCAL_PATH>" in row["source_redacted_path"]


def test_outputs_source_sample_packs_are_gitignored() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["git", "check-ignore", "outputs/source_sample_packs/demo/audio_loops/clip.wav"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0


def test_generated_audio_would_be_blocked_by_privacy_scan(tmp_path: Path) -> None:
    audio_file = tmp_path / "outputs" / "source_sample_packs" / "demo" / "audio_loops" / "clip.wav"
    audio_file.parent.mkdir(parents=True, exist_ok=True)
    audio_file.write_text("C:/Users/private/source.wav", encoding="utf-8")
    payload = scan_privacy_leaks(
        project_root=tmp_path,
        tracked_files=[audio_file],
        changed_files={"outputs/source_sample_packs/demo/audio_loops/clip.wav"},
    )
    assert payload["status"] == "fail"
    assert payload["new_public_leak_count"] >= 1


def test_missing_export_permission_blocks_audio_export(monkeypatch, tmp_path: Path) -> None:
    _patch_build(monkeypatch, tmp_path)
    source_file = tmp_path / "allowed" / "loop.wav"
    _write_wav(source_file)
    _write_json(
        tmp_path / "config" / "source_audio_sample_pack.local.json",
        {
            "allow_audio_loop_export": True,
            "allow_reference_to_midi_starters": True,
            "allowed_loop_lengths_bars": [2],
        },
    )
    _write_json(tmp_path / "local_source_audio_study" / "source_audio_path_map.local.json", {"path_map": [{"path_hash": "h1", "absolute_path": str(source_file)}]})
    _write_jsonl(
        tmp_path / "datasets" / "source_sample_pack" / "source_loop_candidates.jsonl",
        [
            {
                "candidate_id": "c1",
                "source_id": "s1",
                "path_hash": "h1",
                "role": "drums",
                "bar_length": 2,
                "start_seconds": 0.0,
                "duration_seconds": 1.0,
                "reference_only": False,
                "export_allowed": False,
            }
        ],
    )
    manifest, summary = build_source_song_starter_pack.build_pack()
    assert len(manifest["audio_loops"]) == 0
    assert summary["export_violations"] is True
    assert "missing_export_permission" in "\n".join(manifest["policy_violations"])


def test_reaper_bridge_manifest_uses_repo_relative_paths(monkeypatch, tmp_path: Path) -> None:
    _patch_bridge(monkeypatch, tmp_path)
    pack = tmp_path / "outputs" / "source_sample_packs" / "pack_1"
    _write_json(
        pack / "manifest.json",
        {
            "pack_id": "pack_1",
            "audio_loops": [{"path": "outputs/source_sample_packs/pack_1/audio_loops/a.wav"}],
            "midi_starters": [{"path": "outputs/source_sample_packs/pack_1/midi_starters/m1.mid"}],
        },
    )
    bridge, out_path = export_sample_pack_to_reaper_live_bridge.build_reaper_bridge_manifest(pack)
    assert out_path.exists()
    assert bridge["overwrite_user_tracks"] is False
    for track in bridge["tracks"]:
        assert not Path(track["source_path"]).is_absolute()
        assert track["track_name"].startswith("AI Brain")


def test_source_files_are_never_modified(monkeypatch, tmp_path: Path) -> None:
    _patch_build(monkeypatch, tmp_path)
    source_file = tmp_path / "allowed" / "loop.wav"
    _write_wav(source_file, frame_count=44100 * 3)
    before_mtime = source_file.stat().st_mtime_ns
    _write_json(
        tmp_path / "config" / "source_audio_sample_pack.local.json",
        {
            "allow_audio_loop_export": True,
            "allow_reference_to_midi_starters": True,
            "allowed_loop_lengths_bars": [2],
        },
    )
    _write_json(tmp_path / "local_source_audio_study" / "source_audio_path_map.local.json", {"path_map": [{"path_hash": "h1", "absolute_path": str(source_file)}]})
    _write_jsonl(
        tmp_path / "datasets" / "source_sample_pack" / "source_loop_candidates.jsonl",
        [
            {
                "candidate_id": "c1",
                "source_id": "s1",
                "path_hash": "h1",
                "role": "drums",
                "bar_length": 2,
                "start_seconds": 0.0,
                "duration_seconds": 1.0,
                "reference_only": False,
                "export_allowed": True,
            }
        ],
    )
    manifest, _ = build_source_song_starter_pack.build_pack()
    after_mtime = source_file.stat().st_mtime_ns
    assert len(manifest["audio_loops"]) == 1
    assert before_mtime == after_mtime


def test_loop_lengths_respect_allowed_bars(monkeypatch, tmp_path: Path) -> None:
    _patch_build(monkeypatch, tmp_path)
    source_file = tmp_path / "allowed" / "loop.wav"
    _write_wav(source_file)
    _write_json(
        tmp_path / "config" / "source_audio_sample_pack.local.json",
        {
            "allow_audio_loop_export": True,
            "allow_reference_to_midi_starters": True,
            "allowed_loop_lengths_bars": [4],
        },
    )
    _write_json(tmp_path / "local_source_audio_study" / "source_audio_path_map.local.json", {"path_map": [{"path_hash": "h1", "absolute_path": str(source_file)}]})
    _write_jsonl(
        tmp_path / "datasets" / "source_sample_pack" / "source_loop_candidates.jsonl",
        [
            {
                "candidate_id": "c1",
                "source_id": "s1",
                "path_hash": "h1",
                "role": "drums",
                "bar_length": 2,
                "start_seconds": 0.0,
                "duration_seconds": 1.0,
                "reference_only": False,
                "export_allowed": True,
            }
        ],
    )
    manifest, summary = build_source_song_starter_pack.build_pack()
    assert len(manifest["audio_loops"]) == 0
    assert summary["export_violations"] is True
    assert "bar_length_not_allowed" in "\n".join(manifest["policy_violations"])


def test_discovery_uses_controlled_batch_only(monkeypatch, tmp_path: Path) -> None:
    _patch_discovery(monkeypatch, tmp_path)
    source_a = tmp_path / "allowed" / "a_90.wav"
    source_b = tmp_path / "allowed" / "b_90.wav"
    _write_wav(source_a)
    _write_wav(source_b)
    _write_json(
        tmp_path / "config" / "source_audio_sample_pack.local.json",
        {
            "analysis_allowed_roots": [str(tmp_path / "allowed")],
            "export_allowed_roots": [str(tmp_path / "allowed")],
            "sample_pack_allowed_roots": [str(tmp_path / "allowed")],
            "reference_only_roots": [],
            "max_sample_pack_source_items": 1,
            "max_loops_per_source": 1,
            "allowed_loop_lengths_bars": [2],
            "allow_audio_loop_export": True,
            "allow_reference_to_midi_starters": True,
        },
    )
    _write_jsonl(tmp_path / "datasets" / "source_audio_study" / "source_audio_controlled_batch.jsonl", [{"source_id": "s1"}])
    _write_jsonl(
        tmp_path / "datasets" / "source_audio_study" / "source_audio_study_manifest.jsonl",
        [
            {"source_id": "s1", "path_hash": "h1", "redacted_path": "<PRIVATE_LOCAL_PATH>/a_90.wav", "analysis_allowed": True},
            {"source_id": "s2", "path_hash": "h2", "redacted_path": "<PRIVATE_LOCAL_PATH>/b_90.wav", "analysis_allowed": True},
        ],
    )
    _write_json(
        tmp_path / "local_source_audio_study" / "source_audio_path_map.local.json",
        {"path_map": [{"path_hash": "h1", "absolute_path": str(source_a)}, {"path_hash": "h2", "absolute_path": str(source_b)}]},
    )
    _write_json(tmp_path / "reports" / "source_taste_understanding" / "source_database_taste_dossier.json", {})
    _write_jsonl(tmp_path / "datasets" / "model_witnesses" / "source_audio_witness_consensus.jsonl", [])

    candidates, report = discover_source_loop_candidates.build_candidates()
    assert {row["source_id"] for row in candidates} == {"s1"}
    assert report["source_items_considered"] == 1
