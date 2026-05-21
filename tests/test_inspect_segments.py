from __future__ import annotations

import json
from pathlib import Path

from scripts.inspect_segments import inspect_segments


def test_inspect_segments_prints_expected_structure(tmp_path: Path) -> None:
    manifest = {
        "performance_id": "perf_test",
        "source_name": "song.mp3",
        "duration_seconds": 120.0,
        "segmentation_strategy": "energy_v1",
        "musical_segments": [
            {
                "index": 0,
                "global_start_seconds": 0.0,
                "global_end_seconds": 60.0,
                "duration_seconds": 60.0,
                "previous_segment_id": None,
                "next_segment_id": "seg_0001",
                "boundary_confidence": 0.7,
                "boundary_reason": "low_energy_boundary",
                "transcription_window_id": "win_0000",
            }
        ],
        "transcription_windows": [
            {
                "index": 0,
                "global_start_seconds": 0.0,
                "global_end_seconds": 65.0,
                "core_start_seconds": 0.0,
                "core_end_seconds": 60.0,
                "pre_context_seconds": 0.0,
                "post_context_seconds": 5.0,
                "source_segment_ids": ["seg_0000"],
                "status": "success",
                "track_folder": "library/trk_1",
            }
        ],
    }
    manifest_path = tmp_path / "segments_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    lines = inspect_segments(manifest_path)
    text = "\n".join(lines)

    assert "performance_id: perf_test" in text
    assert "segmentation_strategy: energy_v1" in text
    assert "musical_segments_count: 1" in text
    assert "transcription_windows_count: 1" in text
    assert "boundary_reason=low_energy_boundary" in text
    assert "track_folder=library/trk_1" in text
