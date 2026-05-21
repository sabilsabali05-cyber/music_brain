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
    assert manifest["segmentation_parameters"]["boundary_threshold"] == 0.55
    assert manifest["segmentation_parameters"]["min_segment_seconds"] == 30.0
    assert manifest["segmentation_parameters"]["max_segment_seconds"] == 90.0
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
        "analysis_backend": "modal_librosa",
        "analysis_version": "audio_structure_modal_librosa_v1",
        "boundary_candidates": [
            {
                "time_seconds": 62.0,
                "confidence": 0.8,
                "reason": "harmonic_chroma_change",
                "source_feature": "chroma_change",
                "contributing_features": ["chroma_change", "novelty_combined"],
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
            "candidate_density": "dense",
            "fused_candidate_count": 3,
            "returned_candidate_count": 1,
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
    assert manifest["segmentation_diagnostics"]["analysis_backend"] == "modal_librosa"
    assert manifest["segmentation_diagnostics"]["candidate_evaluations"][0]["rejection_reason"] == "accepted"
    assert manifest["segmentation_diagnostics"]["candidate_density"] == "dense"
    assert manifest["segmentation_diagnostics"]["fused_candidate_count"] == 3
    assert manifest["segmentation_diagnostics"]["returned_candidate_count"] == 1
    assert manifest["segmentation_diagnostics"]["candidate_evaluations"][0]["source_feature"] == "chroma_change"
    assert "chroma_change" in manifest["segmentation_diagnostics"]["candidate_evaluations"][0]["contributing_features"]
    assert first_seg["boundary_source"] in {"audio_structure", "fixed_coverage"}
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
    reasons = {
        row["rejection_reason"]
        for row in manifest["segmentation_diagnostics"].get("candidate_evaluations", [])
        if isinstance(row, dict)
    }
    assert "below_threshold" in reasons


def test_audio_structure_lower_threshold_accepts_more_boundaries(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "performance.mp3"
    source.write_bytes(b"fake")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("scripts.segment_audio.probe_duration_seconds", lambda _: 190.0)
    monkeypatch.setattr(
        "scripts.segment_audio.extract_window_audio",
        lambda source_path, output_path, start, end: output_path.parent.mkdir(parents=True, exist_ok=True)
        or output_path.write_bytes(b"x"),
    )

    analysis_root = tmp_path / "samples" / "analysis" / "performance"
    analysis_root.mkdir(parents=True, exist_ok=True)
    analysis_payload = {
        "analysis_version": "audio_structure_v1",
        "analysis_backend": "modal_librosa",
        "boundary_candidates": [
            {
                "time_seconds": 60.0,
                "confidence": 0.50,
                "reason": "onset_density_change",
                "feature_evidence": {
                    "energy_change": 0.2,
                    "onset_change": 0.5,
                    "chroma_change": 0.4,
                    "timbre_change": 0.4,
                    "combined_novelty": 0.5,
                },
            },
            {
                "time_seconds": 120.0,
                "confidence": 0.42,
                "reason": "timbre_change",
                "feature_evidence": {
                    "energy_change": 0.1,
                    "onset_change": 0.35,
                    "chroma_change": 0.3,
                    "timbre_change": 0.5,
                    "combined_novelty": 0.42,
                },
            },
        ],
        "diagnostics": {"available_features": ["rms", "onset_strength", "chroma_change", "timbre_change"]},
    }
    (analysis_root / "structure_analysis.json").write_text(json.dumps(analysis_payload), encoding="utf-8")

    high_threshold_manifest = json.loads(
        segment_audio(
            source,
            strategy="audio_structure",
            target_window_seconds=60.0,
            max_window_seconds=90.0,
            context_seconds=5.0,
            boundary_threshold=0.55,
        ).read_text(encoding="utf-8")
    )
    low_threshold_manifest = json.loads(
        segment_audio(
            source,
            strategy="audio_structure",
            target_window_seconds=60.0,
            max_window_seconds=90.0,
            context_seconds=5.0,
            boundary_threshold=0.35,
        ).read_text(encoding="utf-8")
    )

    assert high_threshold_manifest["segmentation_diagnostics"]["accepted_boundary_count"] == 0
    assert low_threshold_manifest["segmentation_diagnostics"]["accepted_boundary_count"] >= 1


def test_audio_structure_excludes_fixed_candidates_by_default(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "performance.mp3"
    source.write_bytes(b"fake")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("scripts.segment_audio.probe_duration_seconds", lambda _: 130.0)
    monkeypatch.setattr(
        "scripts.segment_audio.extract_window_audio",
        lambda source_path, output_path, start, end: output_path.parent.mkdir(parents=True, exist_ok=True)
        or output_path.write_bytes(b"x"),
    )
    analysis_root = tmp_path / "samples" / "analysis" / "performance"
    analysis_root.mkdir(parents=True, exist_ok=True)
    analysis_payload = {
        "analysis_version": "audio_structure_v1",
        "analysis_backend": "local_light",
        "boundary_candidates": [
            {
                "time_seconds": 62.0,
                "confidence": 0.9,
                "reason": "fixed_interval_fallback",
                "candidate_source": "fixed_coverage",
                "eligible_for_phrase_boundary": False,
                "feature_evidence": {},
            }
        ],
        "diagnostics": {"available_features": ["rms"]},
    }
    (analysis_root / "structure_analysis.json").write_text(json.dumps(analysis_payload), encoding="utf-8")

    manifest = json.loads(
        segment_audio(
            source,
            strategy="audio_structure",
            target_window_seconds=60.0,
            max_window_seconds=90.0,
            context_seconds=5.0,
            boundary_threshold=0.25,
        ).read_text(encoding="utf-8")
    )
    assert manifest["strategy_used"] == "fixed_with_context"
    evaluations = manifest["segmentation_diagnostics"]["candidate_evaluations"]
    assert evaluations[0]["candidate_source"] == "fixed_coverage"
    assert evaluations[0]["eligible_for_phrase_boundary"] is False
    assert evaluations[0]["rejection_reason"] == "fixed_interval_candidate"


def test_audio_structure_allow_fixed_candidates_override(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "performance.mp3"
    source.write_bytes(b"fake")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("scripts.segment_audio.probe_duration_seconds", lambda _: 130.0)
    monkeypatch.setattr(
        "scripts.segment_audio.extract_window_audio",
        lambda source_path, output_path, start, end: output_path.parent.mkdir(parents=True, exist_ok=True)
        or output_path.write_bytes(b"x"),
    )
    analysis_root = tmp_path / "samples" / "analysis" / "performance"
    analysis_root.mkdir(parents=True, exist_ok=True)
    analysis_payload = {
        "analysis_version": "audio_structure_v1",
        "analysis_backend": "local_light",
        "boundary_candidates": [
            {
                "time_seconds": 62.0,
                "confidence": 0.9,
                "reason": "fixed_interval_fallback",
                "candidate_source": "fixed_coverage",
                "eligible_for_phrase_boundary": False,
                "feature_evidence": {},
            }
        ],
        "diagnostics": {"available_features": ["rms"]},
    }
    (analysis_root / "structure_analysis.json").write_text(json.dumps(analysis_payload), encoding="utf-8")

    manifest = json.loads(
        segment_audio(
            source,
            strategy="audio_structure",
            target_window_seconds=60.0,
            max_window_seconds=90.0,
            context_seconds=5.0,
            boundary_threshold=0.25,
            allow_fixed_candidates=True,
        ).read_text(encoding="utf-8")
    )
    assert manifest["strategy_used"] == "audio_structure_v1"
    evaluations = manifest["segmentation_diagnostics"]["candidate_evaluations"]
    assert evaluations[0]["accepted"] is True
    assert evaluations[0]["candidate_source"] == "fixed_coverage"


def test_audio_structure_uses_latest_analysis_pointer(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "performance.mp3"
    source.write_bytes(b"fake")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("scripts.segment_audio.probe_duration_seconds", lambda _: 130.0)
    monkeypatch.setattr(
        "scripts.segment_audio.extract_window_audio",
        lambda source_path, output_path, start, end: output_path.parent.mkdir(parents=True, exist_ok=True)
        or output_path.write_bytes(b"x"),
    )
    analysis_root = tmp_path / "samples" / "analysis" / "performance"
    analysis_run_old = analysis_root / "20260101T000001_modal_librosa_normal"
    analysis_run_new = analysis_root / "20260101T000002_modal_librosa_dense"
    analysis_run_old.mkdir(parents=True, exist_ok=True)
    analysis_run_new.mkdir(parents=True, exist_ok=True)
    old_payload = {
        "analysis_backend": "modal_librosa",
        "analysis_version": "audio_structure_modal_librosa_v1",
        "boundary_candidates": [],
        "diagnostics": {"candidate_density": "normal"},
    }
    new_payload = {
        "analysis_backend": "modal_librosa",
        "analysis_version": "audio_structure_modal_librosa_v1",
        "boundary_candidates": [
            {
                "time_seconds": 62.0,
                "confidence": 0.8,
                "reason": "onset_density_change",
                "source_feature": "onset_strength",
                "contributing_features": ["onset_strength"],
                "feature_evidence": {
                    "energy_change": 0.1,
                    "onset_change": 0.8,
                    "chroma_change": 0.1,
                    "timbre_change": 0.1,
                    "combined_novelty": 0.6,
                },
            }
        ],
        "diagnostics": {"candidate_density": "dense", "fused_candidate_count": 1, "returned_candidate_count": 1},
    }
    old_path = analysis_run_old / "structure_analysis.json"
    new_path = analysis_run_new / "structure_analysis.json"
    old_path.write_text(json.dumps(old_payload), encoding="utf-8")
    new_path.write_text(json.dumps(new_payload), encoding="utf-8")
    (analysis_root / "latest_analysis.txt").write_text(new_path.as_posix(), encoding="utf-8")

    manifest = json.loads(
        segment_audio(
            source,
            strategy="audio_structure",
            target_window_seconds=60.0,
            max_window_seconds=90.0,
            context_seconds=5.0,
        ).read_text(encoding="utf-8")
    )
    assert manifest["segmentation_diagnostics"]["analysis_path"] == new_path.resolve().as_posix()
    assert manifest["segmentation_diagnostics"]["candidate_density"] == "dense"
