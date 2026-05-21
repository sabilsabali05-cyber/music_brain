from __future__ import annotations

import json
from pathlib import Path

from scripts.diagnose_boundaries import diagnose_boundaries


def test_diagnose_boundaries_reads_candidate_evaluations(tmp_path: Path) -> None:
    manifest = {
        "segmentation_diagnostics": {
            "candidate_evaluations": [
                {
                    "time_seconds": 30.0,
                    "confidence": 0.7,
                    "tuned_confidence": 0.72,
                    "accepted": True,
                    "rejection_reason": "accepted",
                    "boundary_reason": "onset_density_change",
                    "nearest_segment_distance": 0.0,
                    "feature_evidence": {
                        "energy_change": 0.1,
                        "onset_change": 0.7,
                        "chroma_change": 0.2,
                        "timbre_change": 0.1,
                        "combined_novelty": 0.72,
                    },
                },
                {
                    "time_seconds": 55.0,
                    "confidence": 0.3,
                    "tuned_confidence": 0.31,
                    "accepted": False,
                    "rejection_reason": "below_threshold",
                    "boundary_reason": "combined_audio_novelty",
                    "nearest_segment_distance": 25.0,
                    "feature_evidence": {
                        "energy_change": 0.05,
                        "onset_change": 0.3,
                        "chroma_change": 0.1,
                        "timbre_change": 0.1,
                        "combined_novelty": 0.31,
                    },
                },
            ]
        }
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    rows = diagnose_boundaries(manifest_path)
    assert len(rows) == 2
    assert rows[0]["accepted"] is True
    assert rows[1]["rejection_reason"] == "below_threshold"
