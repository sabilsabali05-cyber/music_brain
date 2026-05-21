from __future__ import annotations

import json
from pathlib import Path

from scripts.batch_performances import batch_performances
from scripts.ingest_performance import ingest_performance
from scripts.process_performance import process_performance_manifest


def test_ingest_creates_performance_manifest(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    audio = tmp_path / "sample.mp3"
    audio.write_bytes(b"abc123")
    monkeypatch.setattr("scripts.ingest_performance.probe_duration_seconds", lambda _: 61.25)
    manifest_path = ingest_performance(audio)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["status"] == "ingested"
    assert payload["duration_seconds"] == 61.25
    assert payload["checksum"]
    assert Path(payload["source_path"]).name == "sample.mp3"


def test_process_updates_staged_status(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "perf.mp3"
    source.write_bytes(b"sound")
    seg_manifest = tmp_path / "segments_manifest.json"
    seg_manifest.write_text(json.dumps({"transcription_windows": [{"status": "success"}]}), encoding="utf-8")
    perf_manifest = tmp_path / "performance_manifest.json"
    perf_manifest.write_text(
        json.dumps(
            {
                "source_path": source.as_posix(),
                "status": "ingested",
                "analysis_path": None,
                "segments_manifest_path": None,
                "merged_midi_path": None,
                "reports": {},
                "steps": {},
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    def _fake_run(command: list[str]) -> list[str]:
        command_text = " ".join(command)
        if "analyze_audio_structure.py" in command_text:
            return [f"ANALYSIS_PATH={(tmp_path / 'analysis.json').as_posix()}"]
        if "segment_audio.py" in command_text:
            return [f"MANIFEST_PATH={seg_manifest.as_posix()}"]
        if "review_segments.py" in command_text:
            return [f"REVIEW_REPORT_PATH={(tmp_path / 'review.md').as_posix()}"]
        if "stitch_midi.py" in command_text:
            return [f"MERGED_MIDI_PATH={(tmp_path / 'merged.mid').as_posix()}"]
        if "benchmark_segments.py" in command_text:
            return ["successful_windows: 1", "failed_windows: 0"]
        return []

    monkeypatch.setattr("scripts.process_performance._run_command", _fake_run)
    payload = process_performance_manifest(perf_manifest, max_windows=3, no_stitch=False)
    assert payload["status"] == "processed"
    assert payload["analysis_path"]
    assert payload["segments_manifest_path"] == seg_manifest.as_posix()
    assert payload["merged_midi_path"]
    assert payload["steps"]["stitch"]["status"] == "success"


def test_process_skips_stitch_when_manifest_incomplete_by_default(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "perf.mp3"
    source.write_bytes(b"sound")
    seg_manifest = tmp_path / "segments_manifest.json"
    seg_manifest.write_text(
        json.dumps(
            {
                "transcription_windows": [
                    {"window_id": "win_0000", "status": "success"},
                    {"window_id": "win_0001", "status": "pending"},
                ]
            }
        ),
        encoding="utf-8",
    )
    perf_manifest = tmp_path / "performance_manifest.json"
    perf_manifest.write_text(
        json.dumps(
            {
                "source_path": source.as_posix(),
                "status": "ingested",
                "analysis_path": None,
                "segments_manifest_path": None,
                "merged_midi_path": "stale.mid",
                "reports": {},
                "steps": {},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    seen_commands: list[str] = []

    def _fake_run(command: list[str]) -> list[str]:
        command_text = " ".join(command)
        seen_commands.append(command_text)
        if "analyze_audio_structure.py" in command_text:
            return [f"ANALYSIS_PATH={(tmp_path / 'analysis.json').as_posix()}"]
        if "segment_audio.py" in command_text:
            return [f"MANIFEST_PATH={seg_manifest.as_posix()}"]
        if "review_segments.py" in command_text:
            return [f"REVIEW_REPORT_PATH={(tmp_path / 'review.md').as_posix()}"]
        if "benchmark_segments.py" in command_text:
            return ["successful_windows: 1", "failed_windows: 0"]
        if "stitch_midi.py" in command_text:
            return [f"MERGED_MIDI_PATH={(tmp_path / 'merged.mid').as_posix()}"]
        return []

    monkeypatch.setattr("scripts.process_performance._run_command", _fake_run)
    payload = process_performance_manifest(perf_manifest, max_windows=3)
    assert payload["steps"]["stitch"]["status"] == "skipped_incomplete_manifest"
    assert payload["steps"]["stitch"]["reason"] == "manifest has pending or failed windows"
    assert payload["merged_midi_path"] is None
    assert not any("stitch_midi.py" in cmd for cmd in seen_commands)


def test_process_allows_partial_stitch_only_with_flag(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "perf.mp3"
    source.write_bytes(b"sound")
    seg_manifest = tmp_path / "segments_manifest.json"
    seg_manifest.write_text(
        json.dumps(
            {
                "transcription_windows": [
                    {"window_id": "win_0000", "status": "success"},
                    {"window_id": "win_0001", "status": "pending"},
                ]
            }
        ),
        encoding="utf-8",
    )
    perf_manifest = tmp_path / "performance_manifest.json"
    perf_manifest.write_text(
        json.dumps(
            {
                "source_path": source.as_posix(),
                "status": "ingested",
                "analysis_path": None,
                "segments_manifest_path": None,
                "merged_midi_path": None,
                "reports": {},
                "steps": {},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    seen_commands: list[str] = []

    def _fake_run(command: list[str]) -> list[str]:
        command_text = " ".join(command)
        seen_commands.append(command_text)
        if "analyze_audio_structure.py" in command_text:
            return [f"ANALYSIS_PATH={(tmp_path / 'analysis.json').as_posix()}"]
        if "segment_audio.py" in command_text:
            return [f"MANIFEST_PATH={seg_manifest.as_posix()}"]
        if "review_segments.py" in command_text:
            return [f"REVIEW_REPORT_PATH={(tmp_path / 'review.md').as_posix()}"]
        if "benchmark_segments.py" in command_text:
            return ["successful_windows: 1", "failed_windows: 0"]
        if "stitch_midi.py" in command_text:
            return [f"MERGED_MIDI_PATH={(tmp_path / 'merged.mid').as_posix()}"]
        return []

    monkeypatch.setattr("scripts.process_performance._run_command", _fake_run)
    payload = process_performance_manifest(perf_manifest, max_windows=3, allow_partial_stitch=True)
    assert payload["steps"]["stitch"]["status"] == "success"
    assert payload["merged_midi_path"] == (tmp_path / "merged.mid").as_posix()
    assert any("stitch_midi.py" in cmd and "--allow-partial" in cmd for cmd in seen_commands)


def test_process_resume_skips_successful_steps(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "perf.mp3"
    source.write_bytes(b"sound")
    seg_manifest = tmp_path / "segments_manifest.json"
    seg_manifest.write_text(json.dumps({"transcription_windows": [{"status": "success"}]}), encoding="utf-8")
    perf_manifest = tmp_path / "performance_manifest.json"
    perf_manifest.write_text(
        json.dumps(
            {
                "source_path": source.as_posix(),
                "status": "ingested",
                "analysis_path": (tmp_path / "analysis.json").as_posix(),
                "segments_manifest_path": seg_manifest.as_posix(),
                "merged_midi_path": None,
                "reports": {},
                "steps": {
                    "analysis": {"status": "success"},
                    "segmentation": {"status": "success"},
                    "transcription": {"status": "success"},
                    "benchmark": {"status": "success"},
                    "review": {"status": "success"},
                    "stitch": {"status": "pending"},
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    seen: list[str] = []

    def _fake_run(command: list[str]) -> list[str]:
        seen.append(command[1])
        if "stitch_midi.py" in command:
            return [f"MERGED_MIDI_PATH={(tmp_path / 'merged.mid').as_posix()}"]
        return []

    monkeypatch.setattr("scripts.process_performance._run_command", _fake_run)
    payload = process_performance_manifest(perf_manifest, max_windows=3, resume=True)
    assert payload["status"] == "processed"
    assert "scripts/stitch_midi.py" in seen
    assert "scripts/analyze_audio_structure.py" not in seen
    assert "scripts/segment_audio.py" not in seen
    assert "scripts/transcribe_windows.py" not in seen


def test_process_records_failed_step(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "perf.mp3"
    source.write_bytes(b"sound")
    perf_manifest = tmp_path / "performance_manifest.json"
    perf_manifest.write_text(
        json.dumps(
            {
                "source_path": source.as_posix(),
                "status": "ingested",
                "analysis_path": None,
                "segments_manifest_path": None,
                "reports": {},
                "steps": {},
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    def _fake_run(command: list[str]) -> list[str]:
        raise RuntimeError("boom")

    monkeypatch.setattr("scripts.process_performance._run_command", _fake_run)
    try:
        process_performance_manifest(perf_manifest, max_windows=3)
    except RuntimeError:
        pass
    payload = json.loads(perf_manifest.read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    assert payload["steps"]["analysis"]["status"] == "failed"


def test_batch_respects_limits(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    inbox = tmp_path / "performances" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "a.mp3").write_bytes(b"a")
    (inbox / "b.mp3").write_bytes(b"b")
    created_manifests: list[Path] = []
    processed: list[tuple[Path, int]] = []

    def _fake_ingest(audio_path: Path) -> Path:
        manifest = tmp_path / f"{audio_path.stem}.json"
        manifest.write_text(json.dumps({"source_path": audio_path.as_posix()}), encoding="utf-8")
        created_manifests.append(manifest)
        return manifest

    def _fake_process(manifest_path: Path, *, max_windows: int, resume: bool, **_: object) -> dict[str, object]:
        processed.append((manifest_path, max_windows))
        return {"status": "processed"}

    monkeypatch.setattr("scripts.batch_performances.ingest_performance", _fake_ingest)
    monkeypatch.setattr("scripts.batch_performances.process_performance_manifest", _fake_process)
    report_path = batch_performances(inbox, max_performances=1, max_windows=3)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["files_discovered"] == 2
    assert len(report["processed"]) == 1
    assert len(processed) == 1
    assert processed[0][1] == 3
