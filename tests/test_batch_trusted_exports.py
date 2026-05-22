from __future__ import annotations

import json
from pathlib import Path

from scripts.batch_trusted_exports import BatchConfig, batch_trusted_exports
from scripts.validate_batch_report import validate_batch_report


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _make_audio(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"fake-audio")


def _make_manifest(repo_root: Path, name: str, source_path: Path, *, total: int, success: int) -> Path:
    perf_dir = repo_root / "performances" / "library" / name
    seg_dir = repo_root / "samples" / "segments" / name / "run_1"
    seg_manifest = seg_dir / "segments_manifest.json"
    windows = []
    for idx in range(total):
        status = "success" if idx < success else "pending"
        windows.append({"window_id": f"win_{idx:04d}", "status": status})
    _write_json(seg_manifest, {"transcription_windows": windows, "duration_seconds": float(total * 10)})
    manifest = perf_dir / "performance_manifest.json"
    _write_json(
        manifest,
        {
            "performance_id": name,
            "source_path": source_path.resolve().as_posix(),
            "active_segments_manifest_path": seg_manifest.resolve().as_posix(),
            "active_analysis_path": (repo_root / "samples" / "analysis" / name / "run_1" / "structure_analysis.json").resolve().as_posix(),
            "active_merged_midi_path": None,
        },
    )
    return manifest


def _process_stub(manifest_path: Path, *, max_windows: int, **_: object) -> dict:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    seg_path = Path(str(payload.get("active_segments_manifest_path")))
    seg = json.loads(seg_path.read_text(encoding="utf-8"))
    windows = seg.get("transcription_windows", [])
    processed = 0
    for window in windows:
        if not isinstance(window, dict):
            continue
        if str(window.get("status", "pending")) == "pending" and processed < max_windows:
            window["status"] = "success"
            processed += 1
    remaining = any(isinstance(window, dict) and str(window.get("status", "pending")) == "pending" for window in windows)
    if not remaining:
        merged = seg_path.parent / "merged" / "merged_performance.mid"
        merged.parent.mkdir(parents=True, exist_ok=True)
        merged.write_bytes(b"fake-midi")
        payload["active_merged_midi_path"] = merged.resolve().as_posix()
    seg_path.write_text(json.dumps(seg, indent=2), encoding="utf-8")
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def _summary_stub(exports_root: Path) -> tuple[Path, Path]:
    exports_root.mkdir(parents=True, exist_ok=True)
    json_path = exports_root / "training_exports_summary.json"
    md_path = exports_root / "training_exports_summary.md"
    json_path.write_text(json.dumps({"total_performances": 0}), encoding="utf-8")
    md_path.write_text("# stub\n", encoding="utf-8")
    return json_path.resolve(), md_path.resolve()


def test_batch_respects_max_performances(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    inbox = tmp_path / "performances" / "inbox"
    for name in ["a.mp3", "b.mp3", "c.mp3"]:
        _make_audio(inbox / name)
    created: list[Path] = []

    def ingest_stub(source_path: Path) -> Path:
        manifest = _make_manifest(tmp_path, f"perf_{len(created)}", source_path, total=5, success=0)
        created.append(manifest)
        return manifest

    monkeypatch.setattr("scripts.batch_trusted_exports.ingest_performance", ingest_stub)
    monkeypatch.setattr("scripts.batch_trusted_exports.process_performance_manifest", _process_stub)
    monkeypatch.setattr("scripts.batch_trusted_exports._run_completed_pipeline", lambda *args, **kwargs: {})
    monkeypatch.setattr("scripts.batch_trusted_exports.summarize_training_exports", _summary_stub)
    report = batch_trusted_exports(inbox, BatchConfig(max_performances=2, max_windows=3, allow_full_completion=False))
    assert report["summary"]["performances_processed"] == 2


def test_batch_respects_max_windows(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    inbox = tmp_path / "performances" / "inbox"
    src = inbox / "one.mp3"
    _make_audio(src)
    manifest = _make_manifest(tmp_path, "perf_one", src, total=7, success=0)
    monkeypatch.setattr("scripts.batch_trusted_exports._find_existing_manifest", lambda *_: manifest)
    monkeypatch.setattr("scripts.batch_trusted_exports.process_performance_manifest", _process_stub)
    monkeypatch.setattr("scripts.batch_trusted_exports.summarize_training_exports", _summary_stub)
    report = batch_trusted_exports(inbox, BatchConfig(max_performances=1, max_windows=3))
    first = report["performance_results"][0]
    assert first["windows_after"]["successful_windows"] == 3
    assert report["summary"]["windows_processed"] == 3


def test_batch_does_not_duplicate_existing_ingested_performance(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    inbox = tmp_path / "performances" / "inbox"
    src = inbox / "existing.mp3"
    _make_audio(src)
    manifest = _make_manifest(tmp_path, "perf_existing", src, total=3, success=1)
    monkeypatch.setattr("scripts.batch_trusted_exports._find_existing_manifest", lambda *_: manifest)
    monkeypatch.setattr("scripts.batch_trusted_exports.ingest_performance", lambda *_: (_ for _ in ()).throw(RuntimeError("should not ingest")))
    monkeypatch.setattr("scripts.batch_trusted_exports.process_performance_manifest", _process_stub)
    monkeypatch.setattr("scripts.batch_trusted_exports.summarize_training_exports", _summary_stub)
    report = batch_trusted_exports(inbox, BatchConfig(max_performances=1, max_windows=1))
    assert report["summary"]["performances_ingested"] == 0


def test_batch_reuses_active_runs_on_resume(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    inbox = tmp_path / "performances" / "inbox"
    src = inbox / "resume.mp3"
    _make_audio(src)
    manifest = _make_manifest(tmp_path, "perf_resume", src, total=5, success=2)
    monkeypatch.setattr("scripts.batch_trusted_exports._find_existing_manifest", lambda *_: manifest)
    monkeypatch.setattr("scripts.batch_trusted_exports.process_performance_manifest", _process_stub)
    monkeypatch.setattr("scripts.batch_trusted_exports.summarize_training_exports", _summary_stub)
    first = batch_trusted_exports(inbox, BatchConfig(max_performances=1, max_windows=2, allow_full_completion=True))
    second = batch_trusted_exports(inbox, BatchConfig(max_performances=1, max_windows=2, allow_full_completion=True))
    assert first["performance_results"][0]["windows_after"]["successful_windows"] == 4
    assert second["performance_results"][0]["windows_after"]["successful_windows"] == 5


def test_incomplete_cap_is_marked(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    inbox = tmp_path / "performances" / "inbox"
    src = inbox / "cap.mp3"
    _make_audio(src)
    manifest = _make_manifest(tmp_path, "perf_cap", src, total=10, success=0)
    monkeypatch.setattr("scripts.batch_trusted_exports._find_existing_manifest", lambda *_: manifest)
    monkeypatch.setattr("scripts.batch_trusted_exports.process_performance_manifest", _process_stub)
    monkeypatch.setattr("scripts.batch_trusted_exports.summarize_training_exports", _summary_stub)
    report = batch_trusted_exports(inbox, BatchConfig(max_performances=1, max_windows=3))
    assert report["performance_results"][0]["status"] == "incomplete_cap_reached"


def test_complete_run_triggers_downstream_pipeline(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    inbox = tmp_path / "performances" / "inbox"
    src = inbox / "complete.mp3"
    _make_audio(src)
    manifest = _make_manifest(tmp_path, "perf_complete", src, total=2, success=1)
    called = {"value": 0}

    def completed_stub(*args, **kwargs):
        called["value"] += 1
        return {
            "export_folder": (tmp_path / "datasets" / "training_exports" / "perf_complete" / "run_1").as_posix(),
            "export_counts": {
                "accepted_observation_count": 2,
                "weak_label_count": 3,
                "review_required_count": 1,
                "quarantined_count": 0,
            },
        }

    monkeypatch.setattr("scripts.batch_trusted_exports._find_existing_manifest", lambda *_: manifest)
    monkeypatch.setattr("scripts.batch_trusted_exports.process_performance_manifest", _process_stub)
    monkeypatch.setattr("scripts.batch_trusted_exports._run_completed_pipeline", completed_stub)
    monkeypatch.setattr("scripts.batch_trusted_exports.summarize_training_exports", _summary_stub)
    report = batch_trusted_exports(inbox, BatchConfig(max_performances=1, max_windows=2, allow_full_completion=True))
    assert report["performance_results"][0]["status"] == "completed"
    assert called["value"] == 1


def test_failed_step_records_failure_taxonomy(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    inbox = tmp_path / "performances" / "inbox"
    src = inbox / "fail.mp3"
    _make_audio(src)
    manifest = _make_manifest(tmp_path, "perf_fail", src, total=3, success=0)
    monkeypatch.setattr("scripts.batch_trusted_exports._find_existing_manifest", lambda *_: manifest)
    monkeypatch.setattr("scripts.batch_trusted_exports.process_performance_manifest", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr("scripts.batch_trusted_exports.summarize_training_exports", _summary_stub)
    report = batch_trusted_exports(inbox, BatchConfig(max_performances=1, max_windows=1, stop_on_failure=True))
    item = report["performance_results"][0]
    assert item["status"] == "failed"
    assert isinstance(item.get("failure_records"), list) and item["failure_records"]


def test_batch_report_files_written_and_validator_detects_malformed(tmp_path: Path) -> None:
    bad = tmp_path / "reports" / "batches" / "bad.json"
    _write_json(bad, {"summary": {"files_discovered": -1}})
    result = validate_batch_report(bad)
    assert result["status"] == "failed"
