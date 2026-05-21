from __future__ import annotations

import json
from pathlib import Path

from scripts.stitch_midi import build_dry_run_lines


def test_stitch_midi_dry_run_reports_windows_and_warnings(tmp_path: Path) -> None:
    midi_file = tmp_path / "win0.mid"
    midi_file.write_bytes(b"MThd")
    manifest = {
        "segmentation_run_id": "run_123",
        "duration_seconds": 120.0,
        "transcription_windows": [
            {
                "index": 0,
                "status": "success",
                "global_start_seconds": 0.0,
                "global_end_seconds": 35.0,
                "core_start_seconds": 0.0,
                "core_end_seconds": 30.0,
                "midi_path": midi_file.as_posix(),
            },
            {
                "index": 1,
                "status": "failed",
                "global_start_seconds": 25.0,
                "global_end_seconds": 70.0,
                "core_start_seconds": 30.0,
                "core_end_seconds": 65.0,
                "midi_path": None,
            },
        ],
    }
    manifest_path = tmp_path / "segments_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    lines = build_dry_run_lines(manifest_path)
    text = "\n".join(lines)
    assert "windows_total: 2" in text
    assert "windows_with_midi: 1" in text
    assert "windows_missing_or_failed: 1" in text
    assert "warning=context_overlap_present trim_to_core_required" in text
    assert "index=1 status=failed" in text
