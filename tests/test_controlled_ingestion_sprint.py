from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.check_privacy_leaks import scan_privacy_leaks
from scripts.plan_controlled_ingestion_batch import plan_controlled_ingestion_batch
from scripts.run_controlled_ingestion_batch import run_controlled_ingestion_batch


def _write_manifest(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _base_manifest() -> dict:
    return {
        "batch_id": "test_batch",
        "batch_goal": "test",
        "max_song_files": 5,
        "max_sample_library_items": 100,
        "authorization_required": True,
        "allow_modal": False,
        "allow_transcription": False,
        "allow_training_export": False,
        "song_files": [],
        "sample_library_filters": [],
        "notes": [],
    }


def test_example_manifest_validates() -> None:
    manifest_path = Path("config/controlled_batches/controlled_batch.example.json")
    payload = plan_controlled_ingestion_batch(manifest_path)
    assert payload["status"] == "valid"


def test_local_manifest_paths_are_gitignored() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["git", "check-ignore", "config/controlled_batches/demo.local.json"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0


def test_planner_refuses_missing_authorization(tmp_path: Path) -> None:
    manifest = _base_manifest()
    manifest["authorization_required"] = False
    path = _write_manifest(tmp_path, manifest)
    payload = plan_controlled_ingestion_batch(path)
    assert payload["status"] == "invalid"
    assert any("authorization_required" in item for item in payload["errors"])


def test_planner_refuses_folder_mass_dump(tmp_path: Path) -> None:
    manifest = _base_manifest()
    manifest["song_files"] = [{"path": "C:/music/folder/*", "authorized": True, "source": "user_local", "training_allowed": False}]
    path = _write_manifest(tmp_path, manifest)
    payload = plan_controlled_ingestion_batch(path)
    assert payload["status"] == "invalid"
    assert any("mass dump" in item for item in payload["errors"])


def test_planner_caps_song_and_sample_counts(tmp_path: Path) -> None:
    manifest = _base_manifest()
    manifest["max_song_files"] = 7
    manifest["max_sample_library_items"] = 200
    path = _write_manifest(tmp_path, manifest)
    payload = plan_controlled_ingestion_batch(path)
    assert payload["status"] == "invalid"
    assert any("max_song_files cannot exceed 5" in item for item in payload["errors"])
    assert any("max_sample_library_items cannot exceed 100" in item for item in payload["errors"])


def test_runner_is_dry_run_by_default(tmp_path: Path) -> None:
    manifest = _base_manifest()
    manifest["song_files"] = [{"path": "performances/inbox/song.wav", "authorized": True, "source": "user_local", "training_allowed": False}]
    path = _write_manifest(tmp_path, manifest)
    payload = run_controlled_ingestion_batch(path, execute=False)
    assert payload["status"] == "dry_run_success"
    assert payload["provenance"]["audio_processing_performed"] is False


def test_runner_refuses_transcription_without_explicit_allow(tmp_path: Path) -> None:
    manifest = _base_manifest()
    manifest["requested_actions"] = {"transcription_requested": True}
    path = _write_manifest(tmp_path, manifest)
    payload = run_controlled_ingestion_batch(path, execute=False)
    assert payload["status"] == "blocked_invalid_manifest"
    assert any("allow_transcription is false" in item for item in payload["errors"])


def test_runner_refuses_modal_without_explicit_allow(tmp_path: Path) -> None:
    manifest = _base_manifest()
    manifest["requested_actions"] = {"modal_requested": True}
    path = _write_manifest(tmp_path, manifest)
    payload = run_controlled_ingestion_batch(path, execute=False)
    assert payload["status"] == "blocked_invalid_manifest"
    assert any("allow_modal is false" in item for item in payload["errors"])


def test_splice_source_cannot_be_training_source(tmp_path: Path) -> None:
    manifest = _base_manifest()
    manifest["song_files"] = [
        {
            "path": "songs/song.wav",
            "authorized": True,
            "source": "splice_pack",
            "training_allowed": True,
        }
    ]
    path = _write_manifest(tmp_path, manifest)
    payload = plan_controlled_ingestion_batch(path)
    assert payload["status"] == "invalid"
    assert any("Splice source" in item for item in payload["errors"])


def test_reports_include_provenance_and_limitations(tmp_path: Path) -> None:
    manifest = _base_manifest()
    path = _write_manifest(tmp_path, manifest)
    planner = plan_controlled_ingestion_batch(path)
    runner = run_controlled_ingestion_batch(path, execute=False)
    assert "provenance" in planner
    assert "limitations" in planner
    assert planner["provenance"]["audio_processing_performed"] is False
    assert "provenance" in runner
    assert "limitations" in runner
    assert runner["provenance"]["modal_calls_performed"] is False


def test_privacy_scanner_catches_new_public_absolute_paths(tmp_path: Path) -> None:
    public_file = tmp_path / "reports" / "generated.md"
    public_file.parent.mkdir(parents=True, exist_ok=True)
    public_file.write_text("C:/Users/user/OneDrive/Desktop/sounds/kick.wav", encoding="utf-8")
    payload = scan_privacy_leaks(
        project_root=tmp_path,
        tracked_files=[public_file],
        changed_files={"reports/generated.md"},
    )
    assert payload["status"] == "fail"
    assert payload["new_public_leak_count"] >= 1


def test_privacy_scanner_allows_private_ignored_style_files(tmp_path: Path) -> None:
    private_file = tmp_path / "outputs" / "ableton_project_v1" / "AI_Generated_Song_Project" / "private_synplant_seed_paths.md"
    private_file.parent.mkdir(parents=True, exist_ok=True)
    private_file.write_text(r"C:\Users\private\path.wav", encoding="utf-8")
    payload = scan_privacy_leaks(
        project_root=tmp_path,
        tracked_files=[private_file],
        changed_files={"outputs/ableton_project_v1/AI_Generated_Song_Project/private_synplant_seed_paths.md"},
    )
    assert payload["status"] == "ok"
