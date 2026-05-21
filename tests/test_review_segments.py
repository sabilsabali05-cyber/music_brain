from __future__ import annotations

import json
from pathlib import Path

from scripts.review_segments import review_segments


def test_review_segments_generates_markdown_report(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    analysis_path = tmp_path / "samples" / "analysis" / "song" / "structure_analysis.json"
    analysis_path.parent.mkdir(parents=True, exist_ok=True)
    analysis_payload = {
        "frame_hop_seconds": 0.25,
        "boundary_candidates": [
            {
                "time_seconds": 30.0,
                "confidence": 0.8,
                "reason": "harmonic_chroma_change",
                "feature_evidence": {
                    "combined_novelty": 0.8,
                    "chroma_change": 0.9,
                    "timbre_change": 0.4,
                    "onset_change": 0.3,
                    "energy_change": 0.2,
                },
            }
        ],
    }
    analysis_path.write_text(json.dumps(analysis_payload), encoding="utf-8")

    manifest = {
        "source_name": "song.mp3",
        "duration_seconds": 60.0,
        "strategy_requested": "audio_structure",
        "strategy_used": "audio_structure_v1",
        "fallback_used": False,
        "segmentation_run_id": "20260101T000000_audio_structure_v1",
        "segmentation_parameters": {
            "boundary_threshold": 0.55,
            "min_segment_seconds": 30.0,
            "max_segment_seconds": 90.0,
            "rms_weight": 0.2,
            "onset_weight": 0.3,
            "chroma_weight": 0.25,
            "timbre_weight": 0.25,
        },
        "segmentation_diagnostics": {
            "analysis_path": analysis_path.as_posix(),
            "available_features": ["rms", "onset_strength", "chroma_change", "timbre_change"],
            "missing_features": [],
            "candidate_boundary_count": 1,
            "accepted_boundary_count": 1,
        },
        "musical_segments": [
            {
                "index": 0,
                "global_start_seconds": 0.0,
                "global_end_seconds": 30.0,
                "duration_seconds": 30.0,
                "boundary_confidence": 0.8,
                "boundary_reason": "harmonic_chroma_change",
                "feature_evidence": {"combined_novelty": 0.8, "chroma_change": 0.9},
                "boundary_source": "audio_structure_v1",
                "previous_segment_id": None,
                "next_segment_id": "seg_0001",
                "transcription_window_id": "win_0000",
            },
            {
                "index": 1,
                "global_start_seconds": 30.0,
                "global_end_seconds": 60.0,
                "duration_seconds": 30.0,
                "boundary_confidence": 0.6,
                "boundary_reason": "combined_audio_novelty",
                "feature_evidence": {"combined_novelty": 0.6},
                "boundary_source": "audio_structure_v1",
                "previous_segment_id": "seg_0000",
                "next_segment_id": None,
                "transcription_window_id": "win_0001",
            },
        ],
        "transcription_windows": [
            {
                "index": 0,
                "global_start_seconds": 0.0,
                "global_end_seconds": 35.0,
                "core_start_seconds": 0.0,
                "core_end_seconds": 30.0,
                "pre_context_seconds": 0.0,
                "post_context_seconds": 5.0,
                "source_segment_ids": ["seg_0000"],
                "status": "pending",
            }
        ],
    }
    manifest_path = tmp_path / "segments_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    report_path = review_segments(manifest_path)
    text = report_path.read_text(encoding="utf-8")

    assert report_path.exists()
    assert "Segmentation Review: song.mp3" in text
    assert "accepted" in text
    assert "Review Questions" in text
    assert "segmentation_parameters" in text
    assert "boundary_threshold" in text
    assert "Should beat/bar snapping be added?" in text


def test_review_segments_handles_missing_analysis_candidates(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    manifest = {
        "source_name": "ambient.mp3",
        "duration_seconds": 45.0,
        "strategy_requested": "audio_structure",
        "strategy_used": "fixed_with_context",
        "fallback_used": True,
        "segmentation_run_id": "run_x",
        "segmentation_diagnostics": {"analysis_path": "missing.json", "candidate_boundary_count": 0},
        "musical_segments": [],
        "transcription_windows": [],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report_path = review_segments(manifest_path)
    text = report_path.read_text(encoding="utf-8")
    assert "unavailable" in text
