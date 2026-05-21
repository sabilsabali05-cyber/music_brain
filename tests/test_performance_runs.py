from __future__ import annotations

import json
from pathlib import Path

from scripts.list_performance_runs import list_performance_runs
from scripts.performance_runs import ensure_run_tracking_fields
from scripts.process_performance import process_performance_manifest
from scripts.set_active_performance_run import set_active_performance_run


def _write_segments_manifest(path: Path, *, analysis_path: Path, successful: int = 1, pending: int = 0) -> Path:
    windows = [{"window_id": f"win_{index:04d}", "status": "success"} for index in range(successful)]
    windows.extend({"window_id": f"win_p_{index:04d}", "status": "pending"} for index in range(pending))
    payload = {
        "segmentation_diagnostics": {"analysis_path": analysis_path.resolve().as_posix()},
        "transcription_windows": windows,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _base_manifest(source: Path) -> dict[str, object]:
    return {
        "performance_id": "perf_test",
        "source_path": source.as_posix(),
        "status": "ingested",
        "analysis_path": None,
        "segments_manifest_path": None,
        "merged_midi_path": None,
        "reports": {},
        "steps": {},
    }


def test_active_fields_are_backfilled_from_legacy_paths(tmp_path: Path) -> None:
    source = tmp_path / "perf.mp3"
    source.write_bytes(b"sound")
    analysis = tmp_path / "analysis.json"
    analysis.write_text("{}", encoding="utf-8")
    segments = _write_segments_manifest(tmp_path / "segments" / "run_old" / "segments_manifest.json", analysis_path=analysis)
    merged = segments.parent / "merged" / "merged_performance.mid"
    merged.parent.mkdir(parents=True, exist_ok=True)
    merged.write_bytes(b"midi")
    manifest = _base_manifest(source)
    manifest["analysis_path"] = analysis.as_posix()
    manifest["segments_manifest_path"] = segments.as_posix()
    manifest["merged_midi_path"] = merged.as_posix()

    ensure_run_tracking_fields(manifest)

    assert manifest["active_analysis_path"] == analysis.resolve().as_posix()
    assert manifest["active_segments_manifest_path"] == segments.resolve().as_posix()
    assert manifest["active_merged_midi_path"] == merged.resolve().as_posix()
    history = manifest["run_history"]
    assert isinstance(history, list) and len(history) == 1


def test_process_performance_prefers_active_segments_over_legacy(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "perf.mp3"
    source.write_bytes(b"sound")
    analysis = tmp_path / "analysis.json"
    analysis.write_text("{}", encoding="utf-8")
    active_segments = _write_segments_manifest(
        tmp_path / "segments" / "run_active" / "segments_manifest.json",
        analysis_path=analysis,
        successful=1,
    )
    legacy_segments = _write_segments_manifest(
        tmp_path / "segments" / "run_legacy" / "segments_manifest.json",
        analysis_path=analysis,
        successful=1,
    )

    manifest_path = tmp_path / "performance_manifest.json"
    payload = _base_manifest(source)
    payload["analysis_path"] = analysis.as_posix()
    payload["segments_manifest_path"] = legacy_segments.as_posix()
    payload["active_analysis_path"] = analysis.as_posix()
    payload["active_segments_manifest_path"] = active_segments.as_posix()
    payload["active_merged_midi_path"] = None
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    seen: list[str] = []

    def _fake_run(command: list[str]) -> list[str]:
        text = " ".join(command)
        seen.append(text)
        if "benchmark_segments.py" in text:
            return ["successful_windows: 1", "failed_windows: 0"]
        if "review_segments.py" in text:
            return [f"REVIEW_REPORT_PATH={(tmp_path / 'review.md').as_posix()}"]
        return []

    monkeypatch.setattr("scripts.process_performance._run_command", _fake_run)
    process_performance_manifest(manifest_path, max_windows=1, no_stitch=True)
    transcribe_call = next(cmd for cmd in seen if "transcribe_windows.py" in cmd)
    assert active_segments.as_posix() in transcribe_call
    assert legacy_segments.as_posix() not in transcribe_call


def test_force_segmentation_sets_new_active_and_archives_old_run(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "perf.mp3"
    source.write_bytes(b"sound")
    analysis = tmp_path / "analysis.json"
    analysis.write_text("{}", encoding="utf-8")
    old_segments = _write_segments_manifest(
        tmp_path / "segments" / "run_old" / "segments_manifest.json",
        analysis_path=analysis,
        successful=1,
    )
    new_segments = tmp_path / "segments" / "run_new" / "segments_manifest.json"
    manifest_path = tmp_path / "performance_manifest.json"
    payload = _base_manifest(source)
    payload["active_analysis_path"] = analysis.as_posix()
    payload["active_segments_manifest_path"] = old_segments.as_posix()
    payload["analysis_path"] = analysis.as_posix()
    payload["segments_manifest_path"] = old_segments.as_posix()
    payload["steps"] = {
        "transcription": {"status": "success"},
        "benchmark": {"status": "success"},
        "review": {"status": "success"},
        "stitch": {"status": "pending"},
    }
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _fake_run(command: list[str]) -> list[str]:
        text = " ".join(command)
        if "segment_audio.py" in text:
            _write_segments_manifest(new_segments, analysis_path=analysis, successful=2)
            return [f"MANIFEST_PATH={new_segments.as_posix()}"]
        return []

    monkeypatch.setattr("scripts.process_performance._run_command", _fake_run)
    updated = process_performance_manifest(
        manifest_path,
        max_windows=1,
        force_segmentation=True,
        resume=True,
        no_stitch=True,
    )
    assert updated["active_segments_manifest_path"] == new_segments.resolve().as_posix()
    history = updated.get("run_history", [])
    assert isinstance(history, list)
    old_item = next(item for item in history if item.get("run_id") == "run_old")
    new_item = next(item for item in history if item.get("run_id") == "run_new")
    assert old_item.get("status") == "archived"
    assert new_item.get("status") == "active"
    assert new_item.get("source_reason") == "force_segmentation"


def test_set_active_performance_run_switches_to_requested_run(tmp_path: Path) -> None:
    source = tmp_path / "perf.mp3"
    source.write_bytes(b"sound")
    analysis_old = tmp_path / "analysis_old.json"
    analysis_old.write_text("{}", encoding="utf-8")
    analysis_new = tmp_path / "analysis_new.json"
    analysis_new.write_text("{}", encoding="utf-8")
    old_segments = _write_segments_manifest(
        tmp_path / "segments" / "run_old" / "segments_manifest.json",
        analysis_path=analysis_old,
        successful=1,
    )
    new_segments = _write_segments_manifest(
        tmp_path / "segments" / "run_new" / "segments_manifest.json",
        analysis_path=analysis_new,
        successful=3,
    )
    merged = new_segments.parent / "merged" / "merged_performance.mid"
    merged.parent.mkdir(parents=True, exist_ok=True)
    merged.write_bytes(b"midi")

    manifest_path = tmp_path / "performance_manifest.json"
    payload = _base_manifest(source)
    payload["active_analysis_path"] = analysis_old.as_posix()
    payload["active_segments_manifest_path"] = old_segments.as_posix()
    payload["analysis_path"] = analysis_old.as_posix()
    payload["segments_manifest_path"] = old_segments.as_posix()
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    updated = set_active_performance_run(manifest_path, new_segments)
    assert updated["active_segments_manifest_path"] == new_segments.resolve().as_posix()
    assert updated["active_analysis_path"] == analysis_new.resolve().as_posix()
    assert updated["active_merged_midi_path"] == merged.resolve().as_posix()
    history = updated.get("run_history", [])
    assert isinstance(history, list)
    item = next(entry for entry in history if entry.get("run_id") == "run_new")
    assert item.get("source_reason") == "manual_attach"


def test_list_performance_runs_reports_active_and_history(tmp_path: Path) -> None:
    source = tmp_path / "perf.mp3"
    source.write_bytes(b"sound")
    analysis = tmp_path / "analysis.json"
    analysis.write_text("{}", encoding="utf-8")
    segments = _write_segments_manifest(
        tmp_path / "segments" / "run_active" / "segments_manifest.json",
        analysis_path=analysis,
        successful=2,
        pending=1,
    )
    manifest_path = tmp_path / "performance_manifest.json"
    payload = _base_manifest(source)
    payload["performance_id"] = "perf_summary"
    payload["active_analysis_path"] = analysis.as_posix()
    payload["active_segments_manifest_path"] = segments.as_posix()
    payload["run_history"] = [
        {
            "run_id": "run_old",
            "analysis_path": analysis.as_posix(),
            "segments_manifest_path": (tmp_path / "segments" / "run_old" / "segments_manifest.json").as_posix(),
            "merged_midi_path": None,
            "status": "archived",
            "created_at": "2026-01-01T00:00:00+00:00",
            "source_reason": "initial",
            "successful_windows": 1,
            "failed_windows": 0,
            "remaining_windows": 0,
        }
    ]
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    summary = list_performance_runs(manifest_path)
    assert summary["performance_id"] == "perf_summary"
    assert summary["active_segments_manifest_path"] == segments.resolve().as_posix()
    runs = summary["runs"]
    assert isinstance(runs, list)
    assert any(run["run_id"] == "run_old" for run in runs)
    active = next(run for run in runs if run["run_id"] == "run_active")
    assert active["status"] == "active"
    assert active["successful_windows"] == 2
    assert active["remaining_windows"] == 1
