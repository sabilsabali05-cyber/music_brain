from __future__ import annotations

import json
from pathlib import Path

from scripts.transcribe_windows import transcribe_windows


def _write_manifest(path: Path) -> None:
    manifest = {
        "performance_id": "perf_test",
        "source_path": "C:/tmp/perf.mp3",
        "source_name": "perf.mp3",
        "duration_seconds": 120.0,
        "segmentation_strategy": "fixed_with_context",
        "created_at": "2026-01-01T00:00:00Z",
        "musical_segments": [],
        "transcription_windows": [
            {
                "window_id": "win_0000",
                "index": 0,
                "global_start_seconds": 0.0,
                "global_end_seconds": 65.0,
                "core_start_seconds": 0.0,
                "core_end_seconds": 60.0,
                "pre_context_seconds": 0.0,
                "post_context_seconds": 5.0,
                "source_segment_ids": ["seg_0000"],
                "chunk_audio_path": "samples/segments/a/windows/window_0000.wav",
                "status": "success",
                "track_folder": "library/trk_ok",
                "job_report": "library/trk_ok/analysis/job_report.json",
                "midi_path": "library/trk_ok/midi/full_mix.mid",
                "error": None,
            },
            {
                "window_id": "win_0001",
                "index": 1,
                "global_start_seconds": 55.0,
                "global_end_seconds": 120.0,
                "core_start_seconds": 60.0,
                "core_end_seconds": 120.0,
                "pre_context_seconds": 5.0,
                "post_context_seconds": 0.0,
                "source_segment_ids": ["seg_0001"],
                "chunk_audio_path": "samples/segments/a/windows/window_0001.wav",
                "status": "pending",
                "track_folder": None,
                "job_report": None,
                "midi_path": None,
                "error": None,
            },
        ],
        "context_graph": {"adjacency": []},
    }
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def test_transcribe_windows_skips_already_successful_windows(tmp_path: Path, monkeypatch) -> None:
    manifest_path = tmp_path / "segments_manifest.json"
    _write_manifest(manifest_path)
    calls: list[str] = []

    def _fake_submit(chunk_audio_path: str):
        calls.append(chunk_audio_path)
        return True, {
            "track_folder": "library/trk_new",
            "job_report": "library/trk_new/analysis/job_report.json",
            "midi_path": "library/trk_new/midi/full_mix.mid",
        }, ""

    monkeypatch.setattr("scripts.transcribe_windows.submit_window", _fake_submit)
    transcribe_windows(manifest_path, max_windows=2, force=False)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert len(calls) == 1
    assert calls[0].endswith("window_0001.wav")
    assert manifest["transcription_windows"][0]["status"] == "success"
    assert manifest["transcription_windows"][1]["status"] == "success"
