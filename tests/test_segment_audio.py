from __future__ import annotations

import json
from pathlib import Path

from scripts.segment_audio import segment_audio


def test_segment_audio_manifest_contains_segments_and_windows(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "performance.mp3"
    source.write_bytes(b"fake")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("scripts.segment_audio.probe_duration_seconds", lambda _: 125.0)

    def _fake_extract(source_path: Path, output_path: Path, start: float, end: float) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(f"{start}-{end}".encode("utf-8"))

    monkeypatch.setattr("scripts.segment_audio.extract_window_audio", _fake_extract)

    manifest_path = segment_audio(
        source,
        strategy="fixed",
        target_window_seconds=60.0,
        max_window_seconds=90.0,
        context_seconds=5.0,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["segmentation_strategy"] == "fixed_with_context"
    assert len(manifest["musical_segments"]) == len(manifest["transcription_windows"])
    assert len(manifest["musical_segments"]) == 3
    assert manifest["segmentation_run_id"]
    assert manifest["source_audio_sha256"]
    assert manifest["source_audio_size_bytes"] > 0
    assert manifest["source_audio_modified_time"]
    latest_pointer = tmp_path / "samples" / "segments" / "performance" / "latest_manifest.txt"
    assert latest_pointer.exists()
    assert latest_pointer.read_text(encoding="utf-8").strip() == manifest_path.as_posix()


def test_segment_audio_links_and_context_padding(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "performance.mp3"
    source.write_bytes(b"fake")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("scripts.segment_audio.probe_duration_seconds", lambda _: 130.0)
    monkeypatch.setattr("scripts.segment_audio.detect_low_energy_boundaries", lambda _: [62.0, 124.0])
    def _fake_extract(source_path: Path, output_path: Path, start: float, end: float) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"x")

    monkeypatch.setattr("scripts.segment_audio.extract_window_audio", _fake_extract)

    manifest_path = segment_audio(
        source,
        strategy="hybrid",
        target_window_seconds=60.0,
        max_window_seconds=90.0,
        context_seconds=5.0,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    segments = manifest["musical_segments"]
    windows = manifest["transcription_windows"]

    assert manifest["segmentation_strategy"] in {"hybrid_scaffold_with_energy_boundaries", "fixed_with_context"}
    assert segments[0]["previous_segment_id"] is None
    assert segments[0]["next_segment_id"] == segments[1]["segment_id"]
    assert segments[1]["previous_segment_id"] == segments[0]["segment_id"]

    second_window = windows[1]
    assert second_window["pre_context_seconds"] == 5.0
    assert second_window["post_context_seconds"] <= 5.0

    # coverage should reach the source duration on fixed scaffold
    assert windows[-1]["core_end_seconds"] == 130.0


def test_energy_strategy_uses_mocked_boundaries(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "performance.mp3"
    source.write_bytes(b"fake")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("scripts.segment_audio.probe_duration_seconds", lambda _: 130.0)
    monkeypatch.setattr("scripts.segment_audio.detect_low_energy_boundaries", lambda _: [42.0, 86.0])

    def _fake_extract(source_path: Path, output_path: Path, start: float, end: float) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"x")

    monkeypatch.setattr("scripts.segment_audio.extract_window_audio", _fake_extract)

    manifest_path = segment_audio(
        source,
        strategy="energy",
        target_window_seconds=60.0,
        max_window_seconds=90.0,
        context_seconds=5.0,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["segmentation_strategy"] == "energy_v1"
    assert manifest["segmentation_diagnostics"]["accepted_boundary_count"] >= 1
    assert any(seg["boundary_reason"] == "low_energy_boundary" for seg in manifest["musical_segments"])


def test_uncertain_energy_falls_back_clearly(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "performance.mp3"
    source.write_bytes(b"fake")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("scripts.segment_audio.probe_duration_seconds", lambda _: 130.0)
    monkeypatch.setattr("scripts.segment_audio.detect_low_energy_boundaries", lambda _: [])
    monkeypatch.setattr(
        "scripts.segment_audio.extract_window_audio",
        lambda source_path, output_path, start, end: output_path.parent.mkdir(parents=True, exist_ok=True)
        or output_path.write_bytes(b"x"),
    )

    manifest_path = segment_audio(
        source,
        strategy="energy",
        target_window_seconds=60.0,
        max_window_seconds=90.0,
        context_seconds=5.0,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["segmentation_strategy"] == "fixed_with_context"
    assert manifest["segmentation_diagnostics"]["fallback_used"] is True
    assert manifest["musical_segments"][0]["boundary_reason"] == "uncertain_fallback"


def test_segment_audio_creates_unique_run_folders(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "performance.mp3"
    source.write_bytes(b"fake")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("scripts.segment_audio.probe_duration_seconds", lambda _: 121.0)

    def _fake_extract(source_path: Path, output_path: Path, start: float, end: float) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"x")

    monkeypatch.setattr("scripts.segment_audio.extract_window_audio", _fake_extract)
    monkeypatch.setattr("scripts.segment_audio.detect_low_energy_boundaries", lambda _: [61.0])

    first = segment_audio(
        source,
        strategy="energy",
        target_window_seconds=60.0,
        max_window_seconds=90.0,
        context_seconds=5.0,
    )
    second = segment_audio(
        source,
        strategy="fixed",
        target_window_seconds=60.0,
        max_window_seconds=90.0,
        context_seconds=5.0,
    )

    assert first != second
    assert first.parent != second.parent
    latest_pointer = tmp_path / "samples" / "segments" / "performance" / "latest_manifest.txt"
    assert latest_pointer.read_text(encoding="utf-8").strip() == second.as_posix()


def test_audio_structure_strategy_uses_analysis_candidates(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "performance.mp3"
    source.write_bytes(b"fake")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("scripts.segment_audio.probe_duration_seconds", lambda _: 130.0)

    analysis_root = tmp_path / "samples" / "analysis" / "performance"
    analysis_root.mkdir(parents=True, exist_ok=True)
    analysis_payload = {
        "analysis_version": "audio_structure_v1",
        "boundary_candidates": [
            {
                "time_seconds": 62.0,
                "confidence": 0.8,
                "reason": "harmonic_chroma_change",
                "feature_evidence": {
                    "energy_change": 0.3,
                    "onset_change": 0.4,
                    "chroma_change": 0.9,
                    "timbre_change": 0.2,
                    "combined_novelty": 0.8,
                },
            }
        ],
        "diagnostics": {
            "available_features": ["rms", "onset_strength", "chroma_change", "timbre_change"],
            "missing_features": [],
        },
    }
    (analysis_root / "structure_analysis.json").write_text(json.dumps(analysis_payload), encoding="utf-8")

    def _fake_extract(source_path: Path, output_path: Path, start: float, end: float) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"x")

    monkeypatch.setattr("scripts.segment_audio.extract_window_audio", _fake_extract)
    manifest_path = segment_audio(
        source,
        strategy="audio_structure",
        target_window_seconds=60.0,
        max_window_seconds=90.0,
        context_seconds=5.0,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    first_seg = manifest["musical_segments"][0]
    assert manifest["strategy_requested"] == "audio_structure"
    assert manifest["segmentation_diagnostics"]["candidate_boundary_count"] == 1
    assert first_seg["boundary_source"] in {"audio_structure_v1", "fixed"}
    assert "feature_evidence" in first_seg


def test_audio_structure_weak_candidates_fallback_to_fixed(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "performance.mp3"
    source.write_bytes(b"fake")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("scripts.segment_audio.probe_duration_seconds", lambda _: 130.0)

    analysis_root = tmp_path / "samples" / "analysis" / "performance"
    analysis_root.mkdir(parents=True, exist_ok=True)
    analysis_payload = {
        "analysis_version": "audio_structure_v1",
        "boundary_candidates": [
            {
                "time_seconds": 62.0,
                "confidence": 0.2,
                "reason": "combined_audio_novelty",
                "feature_evidence": {
                    "energy_change": 0.1,
                    "onset_change": 0.1,
                    "chroma_change": 0.1,
                    "timbre_change": 0.1,
                    "combined_novelty": 0.2,
                },
            }
        ],
        "diagnostics": {"available_features": ["rms"], "missing_features": ["chroma_change"]},
    }
    (analysis_root / "structure_analysis.json").write_text(json.dumps(analysis_payload), encoding="utf-8")
    monkeypatch.setattr(
        "scripts.segment_audio.extract_window_audio",
        lambda source_path, output_path, start, end: output_path.parent.mkdir(parents=True, exist_ok=True)
        or output_path.write_bytes(b"x"),
    )

    manifest_path = segment_audio(
        source,
        strategy="audio_structure",
        target_window_seconds=60.0,
        max_window_seconds=90.0,
        context_seconds=5.0,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["strategy_used"] == "fixed_with_context"
    assert manifest["fallback_used"] is True
    assert manifest["musical_segments"][0]["boundary_reason"] == "uncertain_audio_structure_fallback"
