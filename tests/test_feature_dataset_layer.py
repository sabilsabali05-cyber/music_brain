from __future__ import annotations

import json
from pathlib import Path

from mido import Message, MidiFile, MidiTrack

from scripts.build_ai_training_records import build_ai_training_records
from scripts.extract_feature_pack import extract_feature_pack
from scripts.extract_harmony_features import extract_harmony_features
from scripts.extract_rhythm_features import extract_rhythm_features
from scripts.tag_performance_features import tag_performance_features
from scripts.validate_feature_pack import validate_feature_pack


def _write_midi(path: Path, notes: list[int], spacing_ticks: int = 120) -> Path:
    midi = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    midi.tracks.append(track)
    for note in notes:
        track.append(Message("note_on", note=note, velocity=70, time=spacing_ticks))
        track.append(Message("note_off", note=note, velocity=0, time=120))
    path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(path)
    return path


def _write_manifests(
    tmp_path: Path,
    *,
    include_merged: bool,
    include_window_midis: bool,
    pending_windows: int = 0,
    sparse: bool = False,
) -> tuple[Path, Path, Path | None]:
    analysis = tmp_path / "analysis" / "structure_analysis.json"
    analysis.parent.mkdir(parents=True, exist_ok=True)
    analysis.write_text("{}", encoding="utf-8")

    segments = tmp_path / "samples" / "segments" / "source_a" / "run_123" / "segments_manifest.json"
    midi_window_0 = tmp_path / "windows" / "win0.mid"
    midi_window_1 = tmp_path / "windows" / "win1.mid"
    if include_window_midis:
        _write_midi(midi_window_0, [60, 64] if sparse else [60, 64, 67, 72])
        _write_midi(midi_window_1, [62, 65] if sparse else [62, 65, 69, 74])
    merged_path = None
    if include_merged:
        merged_path = tmp_path / "samples" / "segments" / "source_a" / "run_123" / "merged" / "merged_performance.mid"
        _write_midi(merged_path, [60, 64] if sparse else [60, 62, 64, 65, 67, 69, 71, 72], spacing_ticks=90)

    windows = []
    for idx in range(2):
        midi_path = (midi_window_0 if idx == 0 else midi_window_1).as_posix() if include_window_midis else None
        windows.append(
            {
                "window_id": f"win_{idx:04d}",
                "index": idx,
                "status": "success",
                "core_start_seconds": float(idx * 10),
                "core_end_seconds": float((idx + 1) * 10),
                "midi_path": midi_path,
            }
        )
    for idx in range(pending_windows):
        windows.append(
            {
                "window_id": f"win_p_{idx:04d}",
                "index": idx + 2,
                "status": "pending",
                "core_start_seconds": 20.0,
                "core_end_seconds": 30.0,
                "midi_path": None,
            }
        )
    segments_payload = {
        "duration_seconds": 30.0,
        "segmentation_diagnostics": {"analysis_path": analysis.resolve().as_posix()},
        "musical_segments": [{"segment_id": "seg_0000"}, {"segment_id": "seg_0001"}],
        "transcription_windows": windows,
    }
    segments.parent.mkdir(parents=True, exist_ok=True)
    segments.write_text(json.dumps(segments_payload, indent=2), encoding="utf-8")

    performance_manifest = tmp_path / "performances" / "library" / "perf_1" / "performance_manifest.json"
    performance_manifest.parent.mkdir(parents=True, exist_ok=True)
    performance_manifest.write_text(
        json.dumps(
            {
                "performance_id": "perf_1",
                "source_name": "fake.mp3",
                "source_path": (tmp_path / "fake.mp3").as_posix(),
                "active_analysis_path": analysis.resolve().as_posix(),
                "active_segments_manifest_path": segments.resolve().as_posix(),
                "active_merged_midi_path": merged_path.resolve().as_posix() if merged_path else None,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return performance_manifest, segments, merged_path.resolve() if merged_path else None


def test_extractors_prefer_merged_midi(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    performance_manifest, _, merged_path = _write_manifests(
        tmp_path,
        include_merged=True,
        include_window_midis=True,
    )
    rhythm_path = extract_rhythm_features(performance_manifest)
    harmony_path = extract_harmony_features(performance_manifest)
    rhythm_payload = json.loads(rhythm_path.read_text(encoding="utf-8"))
    harmony_payload = json.loads(harmony_path.read_text(encoding="utf-8"))
    assert rhythm_payload["summary"]["source_mode"] == "merged"
    assert harmony_payload["summary"]["source_mode"] == "merged"
    assert rhythm_payload["records"][0]["source_artifact_paths"]["midi_source_path"] == merged_path.as_posix()


def test_extractors_fallback_to_windows_and_capture_low_confidence(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    performance_manifest, _, _ = _write_manifests(
        tmp_path,
        include_merged=False,
        include_window_midis=True,
        pending_windows=1,
        sparse=True,
    )
    rhythm_path = extract_rhythm_features(performance_manifest)
    harmony_path = extract_harmony_features(performance_manifest)
    rhythm_payload = json.loads(rhythm_path.read_text(encoding="utf-8"))
    harmony_payload = json.loads(harmony_path.read_text(encoding="utf-8"))
    assert rhythm_payload["summary"]["source_mode"] == "window_fallback"
    assert harmony_payload["summary"]["source_mode"] == "window_fallback"
    assert rhythm_payload["summary"]["low_confidence_record_count"] >= 1
    assert harmony_payload["summary"]["low_confidence_record_count"] >= 1
    assert any("fall" in str(note).lower() for note in rhythm_payload["limitations"])


def test_extract_feature_pack_and_validation_outputs_expected_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    performance_manifest, _, _ = _write_manifests(
        tmp_path,
        include_merged=False,
        include_window_midis=True,
    )
    feature_dir = extract_feature_pack(performance_manifest)
    expected_paths = [
        feature_dir / "feature_pack_manifest.json",
        feature_dir / "rhythm_features.json",
        feature_dir / "harmony_features.json",
        feature_dir / "tags.json",
        feature_dir / "ai_training_records.json",
    ]
    for candidate in expected_paths:
        assert candidate.exists()
    summary = validate_feature_pack(performance_manifest)
    assert summary["status"] == "success"
    assert summary["tag_count"] > 0


def test_manual_pipeline_generates_tags_and_ai_records(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    performance_manifest, _, _ = _write_manifests(
        tmp_path,
        include_merged=True,
        include_window_midis=True,
    )
    rhythm_path = extract_rhythm_features(performance_manifest)
    harmony_path = extract_harmony_features(performance_manifest)
    tags_path = tag_performance_features(performance_manifest)
    ai_path = build_ai_training_records(performance_manifest)

    rhythm_payload = json.loads(rhythm_path.read_text(encoding="utf-8"))
    harmony_payload = json.loads(harmony_path.read_text(encoding="utf-8"))
    tags_payload = json.loads(tags_path.read_text(encoding="utf-8"))
    ai_payload = json.loads(ai_path.read_text(encoding="utf-8"))

    assert len(rhythm_payload["records"]) >= 1
    assert len(harmony_payload["records"]) >= 1
    assert tags_payload["tag_count"] == len(tags_payload["tags"])
    assert ai_payload["record_count"] == len(ai_payload["records"])
