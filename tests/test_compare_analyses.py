from __future__ import annotations

import json
from pathlib import Path

from scripts.compare_analyses import compare_analyses


def _write_analysis_run(
    root: Path,
    run_id: str,
    *,
    density: str,
    candidate_count: int,
    fused_count: int,
    returned_count: int,
) -> Path:
    run_dir = root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    candidates = [
        {
            "time_seconds": 10.0 + i,
            "confidence": 0.9 - i * 0.05,
            "source_feature": "novelty_combined",
            "contributing_features": ["novelty_combined"],
        }
        for i in range(candidate_count)
    ]
    payload = {
        "analysis_backend": "modal_librosa",
        "analysis_version": "audio_structure_modal_librosa_v1",
        "analysis_run_id": run_id,
        "boundary_candidates": candidates,
        "diagnostics": {
            "candidate_density": density,
            "available_features": ["rms", "onset_strength", "chroma_change", "timbre_change", "novelty_combined"],
            "missing_features": [],
            "raw_peak_count_by_feature": {
                "rms": candidate_count,
                "onset_strength": candidate_count,
                "chroma_change": candidate_count,
                "timbre_change": candidate_count,
                "novelty_combined": candidate_count,
            },
            "fused_candidate_count": fused_count,
            "returned_candidate_count": returned_count,
        },
    }
    path = run_dir / "structure_analysis.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def test_compare_analyses_summarizes_runs(tmp_path: Path) -> None:
    source_folder = tmp_path / "analysis" / "piece"
    _write_analysis_run(
        source_folder,
        "20260101T000001_modal_librosa_normal",
        density="normal",
        candidate_count=3,
        fused_count=3,
        returned_count=3,
    )
    _write_analysis_run(
        source_folder,
        "20260101T000002_modal_librosa_dense",
        density="dense",
        candidate_count=6,
        fused_count=6,
        returned_count=6,
    )
    rows = compare_analyses(source_folder)
    assert len(rows) == 2
    dense_row = next(row for row in rows if row["density"] == "dense")
    assert dense_row["boundary_candidate_count"] == 6
    assert dense_row["fused_candidate_count"] == 6
    assert dense_row["returned_candidate_count"] == 6
    assert "novelty_combined" in str(dense_row["top_candidates"])
