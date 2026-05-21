from __future__ import annotations

import json
from pathlib import Path

from scripts.analyze_audio_structure import (
    analyze_audio_structure,
    analyze_audio_structure_modal,
    audio_analysis_diagnostics,
    fuse_boundary_candidates,
)


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
    assert payload["analysis_backend"] == "local_light"
    assert "features" in payload
    assert "boundary_candidates" in payload
    assert "diagnostics" in payload
    assert "rms" in payload["features"]
    assert "onset_strength" in payload["features"]
    assert "chroma_change" in payload["features"]
    assert "timbre_change" in payload["features"]
    assert "novelty_combined" in payload["features"]


def test_modal_librosa_client_writes_expected_schema(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "song.mp3"
    source.write_bytes(b"fake")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("scripts.analyze_audio_structure.probe_duration_seconds", lambda _: 120.0)

    def _fake_modal_call(audio_bytes: bytes, source_name: str, options: dict[str, object]) -> dict[str, object]:
        assert audio_bytes
        assert source_name == "song.mp3"
        return {
            "analysis_backend": "modal_librosa",
            "analysis_version": "audio_structure_modal_librosa_v1",
            "frame_hop_seconds": 0.25,
            "features": {
                "rms": [0.1, 0.2],
                "onset_strength": [0.2, 0.3],
                "chroma_change": [0.3, 0.4],
                "timbre_change": [0.4, 0.5],
                "novelty_combined": [0.5, 0.6],
            },
            "boundary_candidates": [
                {
                    "time_seconds": 30.0,
                    "confidence": 0.8,
                    "reason": "harmonic_chroma_change",
                    "feature_evidence": {
                        "energy_change": 0.1,
                        "onset_change": 0.2,
                        "chroma_change": 0.9,
                        "timbre_change": 0.3,
                        "combined_novelty": 0.8,
                    },
                }
            ],
            "diagnostics": {
                "fallback_recommended": False,
                "candidate_boundary_count": 1,
                "accepted_boundary_count": 1,
                "rejected_boundary_count": 0,
                "available_features": [
                    "rms",
                    "onset_strength",
                    "chroma_change",
                    "timbre_change",
                    "novelty_combined",
                ],
                "missing_features": [],
                "notes": ["mock modal"],
            },
        }

    analysis_path = analyze_audio_structure_modal(source, remote_call=_fake_modal_call)
    payload = json.loads(analysis_path.read_text(encoding="utf-8"))
    assert payload["analysis_backend"] == "modal_librosa"
    assert payload["analysis_version"] == "audio_structure_modal_librosa_v1"
    assert "chroma_change" in payload["features"]
    assert "timbre_change" in payload["features"]
    assert payload["diagnostics"]["available_features"]


def test_audio_analysis_diagnostics_reports_modal_lookup(monkeypatch) -> None:
    class _Fn:
        @staticmethod
        def from_name(app_name: str, fn_name: str):
            assert app_name == "music-brain-v2"
            assert fn_name == "analyze_audio_structure_modal"
            return object()

    class _ModalStub:
        Function = _Fn

    import sys

    monkeypatch.setitem(sys.modules, "modal", _ModalStub())
    diagnostics = audio_analysis_diagnostics()
    assert diagnostics["local_light_available"] is True
    assert diagnostics["modal_librosa_function_lookup_ok"] is True
    assert diagnostics["modal_librosa_cpu_only"] is True
