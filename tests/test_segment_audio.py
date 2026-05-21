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


def test_segment_audio_links_and_context_padding(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "performance.mp3"
    source.write_bytes(b"fake")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("scripts.segment_audio.probe_duration_seconds", lambda _: 130.0)
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
    assert second_window["post_context_seconds"] == 5.0

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
