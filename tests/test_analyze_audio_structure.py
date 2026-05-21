from __future__ import annotations

import json
from pathlib import Path

from scripts.analyze_audio_structure import analyze_audio_structure, fuse_boundary_candidates


def test_fuse_boundary_candidates_accepts_obvious_peaks() -> None:
    curves = {
        "rms": [0.1, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2],
        "onset_strength": [0.0, 0.1, 0.85, 0.2, 0.1, 0.9, 0.2, 0.1],
        "chroma_change": [0.0, 0.05, 0.8, 0.1, 0.1, 0.7, 0.1, 0.1],
        "timbre_change": [0.0, 0.05, 0.7, 0.1, 0.1, 0.75, 0.1, 0.1],
        "novelty_combined": [0.0, 0.1, 0.9, 0.2, 0.1, 0.92, 0.1, 0.1],
    }
    candidates, diagnostics = fuse_boundary_candidates(
        feature_curves=curves,
        frame_hop_seconds=10.0,
        duration_seconds=90.0,
        target_window_seconds=30.0,
        max_window_seconds=45.0,
        min_segment_seconds=10.0,
        confidence_threshold=0.55,
    )
    assert diagnostics["candidate_boundary_count"] >= 1
    assert diagnostics["accepted_boundary_count"] >= 1
    assert any(float(c["confidence"]) >= 0.55 for c in candidates)


def test_analyze_audio_structure_writes_expected_schema(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "song.mp3"
    source.write_bytes(b"fake")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("scripts.analyze_audio_structure.probe_duration_seconds", lambda _: 120.0)
    monkeypatch.setattr(
        "scripts.analyze_audio_structure.extract_analysis_wav",
        lambda source_path, output_path: output_path.parent.mkdir(parents=True, exist_ok=True)
        or output_path.write_bytes(b"wav"),
    )
    monkeypatch.setattr(
        "scripts.analyze_audio_structure._read_wav_samples",
        lambda wav_path: ([0.01, -0.02, 0.03, -0.03] * 2000, 22050),
    )

    analysis_path = analyze_audio_structure(source)
    payload = json.loads(analysis_path.read_text(encoding="utf-8"))

    assert payload["analysis_version"] == "audio_structure_v1"
    assert "features" in payload
    assert "boundary_candidates" in payload
    assert "diagnostics" in payload
    assert "rms" in payload["features"]
    assert "onset_strength" in payload["features"]
    assert "chroma_change" in payload["features"]
    assert "timbre_change" in payload["features"]
    assert "novelty_combined" in payload["features"]
