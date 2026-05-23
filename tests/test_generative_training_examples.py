from __future__ import annotations

import json
from pathlib import Path

from mido import Message, MidiFile, MidiTrack

from scripts.build_generative_training_examples import build_generative_training_examples
from scripts.build_generative_training_examples import _task_allowed
from scripts.diagnose_generative_examples import diagnose_generative_examples
from scripts.diagnose_generative_pairing import diagnose_generative_pairing
from scripts.validate_generative_training_examples import validate_generative_training_examples


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_midi(path: Path, notes: list[int]) -> None:
    midi = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    midi.tracks.append(track)
    for idx, note in enumerate(notes):
        track.append(Message("note_on", note=note, velocity=80 + (idx % 20), time=4800))
        track.append(Message("note_off", note=note, velocity=0, time=2400))
    path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(path.as_posix())


def _setup_workspace(
    tmp_path: Path,
    *,
    long_form: bool = False,
    conservative_routing: bool = False,
    review_required: bool = True,
) -> tuple[Path, str, str]:
    performance_id = "sunday_service_choir_perf" if long_form else "perf_gen"
    run_id = "run_gen_1"
    audio = tmp_path / "audio" / "src.wav"
    audio.parent.mkdir(parents=True, exist_ok=True)
    audio.write_bytes(b"RIFFfake")
    merged = tmp_path / "samples" / "segments" / performance_id / run_id / "merged" / "merged_performance.mid"
    _write_midi(merged, [48, 50, 52, 53, 55, 57, 59, 60] * 80)
    windows_dir = tmp_path / "samples" / "segments" / performance_id / run_id / "windows"
    w0 = windows_dir / "w0.mid"
    w1 = windows_dir / "w1.mid"
    w2 = windows_dir / "w2.mid"
    w3 = windows_dir / "w3.mid"
    _write_midi(w0, [48, 50, 52, 53, 55, 57, 59, 60])
    _write_midi(w1, [60, 62, 64, 65, 67, 69, 71, 72, 74])
    _write_midi(w2, [72, 74, 76, 77, 79, 81, 83, 84])
    _write_midi(w3, [36, 36, 38, 40, 41, 43, 45, 47])

    segments_manifest = tmp_path / "samples" / "segments" / performance_id / run_id / "segments_manifest.json"
    windows_payload = [
        {"window_id": "w0", "index": 0, "core_start_seconds": 0.0, "core_end_seconds": 10.0, "midi_path": w0.resolve().as_posix(), "status": "success"},
        {"window_id": "w1", "index": 1, "core_start_seconds": 10.0, "core_end_seconds": 20.0, "midi_path": w1.resolve().as_posix(), "status": "success"},
        {"window_id": "w2", "index": 2, "core_start_seconds": 20.0, "core_end_seconds": 30.0, "midi_path": w2.resolve().as_posix(), "status": "success"},
        {"window_id": "w3", "index": 3, "core_start_seconds": 30.0, "core_end_seconds": 40.0, "midi_path": w3.resolve().as_posix(), "status": "success"},
    ]
    if long_form:
        for idx in range(4, 16):
            start = float(idx * 10)
            end = float((idx + 1) * 10)
            w_path = windows_dir / f"w{idx}.mid"
            _write_midi(w_path, [48 + (idx % 12), 52 + (idx % 12), 55 + (idx % 12), 60 + (idx % 12)] * 4)
            windows_payload.append(
                {
                    "window_id": f"w{idx}",
                    "index": idx,
                    "core_start_seconds": start,
                    "core_end_seconds": end,
                    "midi_path": w_path.resolve().as_posix(),
                    "status": "success",
                }
            )
    _write_json(
        segments_manifest,
        {
            "duration_seconds": 160.0 if long_form else 40.0,
            "musical_segments": [
                {"segment_id": "s0", "index": 0, "global_start_seconds": 0.0, "global_end_seconds": 10.0, "section_label": "intro"},
                {"segment_id": "s1", "index": 1, "global_start_seconds": 10.0, "global_end_seconds": 20.0, "section_label": "verse"},
                {"segment_id": "s2", "index": 2, "global_start_seconds": 20.0, "global_end_seconds": 30.0, "section_label": "hook"},
                {"segment_id": "s3", "index": 3, "global_start_seconds": 30.0, "global_end_seconds": 40.0, "section_label": "outro"},
            ],
            "transcription_windows": windows_payload,
        },
    )
    perf_manifest = tmp_path / "performances" / "library" / performance_id / "performance_manifest.json"
    _write_json(
        perf_manifest,
        {
            "performance_id": performance_id,
            "source_name": "sunday_service_choir_live.wav" if long_form else "src.wav",
            "source_path": audio.resolve().as_posix(),
            "active_segments_manifest_path": segments_manifest.resolve().as_posix(),
            "active_merged_midi_path": merged.resolve().as_posix(),
        },
    )
    feature_dir = tmp_path / "features" / "performances" / performance_id / run_id
    _write_json(feature_dir / "feature_pack_manifest.json", {"performance_id": performance_id, "segment_run_id": run_id})
    _write_json(
        feature_dir / "rhythm_features.json",
        {
            "records": [],
            "rhythm_motifs": {"motifs": [{"motif_id": "m1"}]},
            "rhythm_motif_groups": [
                {
                    "motif_group_id": "mg1",
                    "region_ids": ["route_w1", "route_w2"],
                    "window_ids": ["w1", "w2"],
                    "rhythm_family_confidence": 0.7,
                }
            ],
        },
    )
    _write_json(feature_dir / "harmony_features.json", {"records": [], "chord_movement_summary": {}})
    _write_json(feature_dir / "rhythm_time" / "meter_time_features.json", {"confidence": 0.7, "ambiguity": 0.3, "summary": {"subdivision_histogram": {"straight_eighths": 3}, "macro_section_candidates": ["intro", "verse"]}, "beat_meter_hypotheses": [{"meter": "4/4", "confidence": 0.7, "ambiguity": 0.3}]})
    _write_json(
        feature_dir / "pitch_harmony" / "pitch_harmony_features.json",
        {
            "summary": {},
            "macro_record": {"key_hypotheses": [{"key": "C", "confidence": 0.7}], "register_density_arc": {}},
            "interval_analysis": [{"x": 1}],
            "melody_contour": [{"x": 1}],
            "harmony_sonority": [{"ambiguity": 0.2}],
            "chord_movement": [{"x": 1}],
            "counterpoint": [{"x": 1}],
            "tuning_system": [{"microtonal_analysis_available": False}],
        },
    )
    _write_json(feature_dir / "tags.json", {"top_unique_tags": [{"tag": "gospel_choir"}, {"tag": "dense_activity"}]})
    route_rows = [
        {"route_id": "route_w0", "source_record_id": "route_w0", "start_seconds": 0.0, "end_seconds": 10.0, "content_state": "rhythm_dominant", "confidence": 0.8},
        {"route_id": "route_w1", "source_record_id": "route_w1", "start_seconds": 10.0, "end_seconds": 20.0, "content_state": "rhythm_dominant", "confidence": 0.8},
        {
            "route_id": "route_w2",
            "source_record_id": "route_w2",
            "start_seconds": 20.0,
            "end_seconds": 30.0,
            "content_state": "rhythm_dominant" if conservative_routing else "polyphonic_full_mix",
            "confidence": 0.85,
        },
        {"route_id": "route_w3", "source_record_id": "route_w3", "start_seconds": 30.0, "end_seconds": 40.0, "content_state": "silence_or_noise", "confidence": 0.95},
    ]
    if long_form:
        for idx in range(4, 16):
            start = float(idx * 10)
            end = float((idx + 1) * 10)
            state = "polyphonic_full_mix" if idx % 3 else "rhythm_dominant"
            route_rows.append(
                {
                    "route_id": f"route_w{idx}",
                    "source_record_id": f"route_w{idx}",
                    "start_seconds": start,
                    "end_seconds": end,
                    "content_state": state,
                    "confidence": 0.82,
                }
            )
    _write_json(
        feature_dir / "routing" / "content_region_routes.json",
        {"routes": route_rows},
    )
    _write_json(feature_dir / "routing" / "analysis_routing_decisions.json", {"decisions": []})
    _write_json(
        feature_dir / "trust" / "transcription_reliability.json",
        {
            "windows": [
                {"window_id": "w0", "transcription_reliability_score": 0.9},
                {"window_id": "w1", "transcription_reliability_score": 0.85},
                {"window_id": "w2", "transcription_reliability_score": 0.4},
                {"window_id": "w3", "transcription_reliability_score": 0.3},
            ]
        },
    )
    _write_json(
        feature_dir / "trust" / "quality_gates.json",
        {"overall_quality_status": "review_required" if review_required else "accepted"},
    )
    ext = feature_dir / "external_model_features"
    _write_json(ext / "essentia_features.json", {"status": "success"})
    _write_json(ext / "music21_features.json", {"status": "success"})
    _write_json(ext / "model_consensus.json", {"consensus_status": "conflicted", "disagreements": ["tonal conflict"], "unresolved_conflicts": ["tonal_center_conflict"]})
    _write_json(ext / "model_witness_comparison.json", {"provider_status": {"essentia": "success", "music21": "success"}})
    return perf_manifest, performance_id, run_id


def test_builder_creates_continuation_infill_and_domain_tasks(tmp_path: Path, monkeypatch) -> None:
    manifest, performance_id, run_id = _setup_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    jsonl_path, manifest_path, _ = build_generative_training_examples(manifest)
    assert jsonl_path.exists()
    assert manifest_path.exists()
    rows = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    tasks = {row["task_type"] for row in rows}
    assert "continuation" in tasks
    assert "infill_missing_region" in tasks
    assert "groove_continuation" in tasks
    assert "harmony_continuation" in tasks
    assert "melody_continuation" in tasks
    assert "motif_transformation" in tasks
    infill = next(row for row in rows if row["task_type"] == "infill_missing_region")
    assert infill["context_start_seconds"] <= infill["target_start_seconds"] <= infill["target_end_seconds"] <= infill["context_end_seconds"]
    # silence_or_noise stays excluded rather than promoted.
    silence_rows = [row for row in rows if row["conditioning"]["content_state"] == "silence_or_noise"]
    assert all(row["split_recommendation"] == "exclude" for row in silence_rows)
    # weak style tags are conditioning-only
    assert "style_tags_weak" in rows[0]["conditioning"]
    assert "style_tags_ground_truth" not in rows[0]["conditioning"]
    assert "split_reason_codes" in rows[0]
    assert "quality_component_breakdown" in rows[0]
    assert isinstance(rows[0]["split_reason_codes"], list)
    assert isinstance(rows[0]["quality_component_breakdown"], dict)
    assert any(row["split_recommendation"] in {"review", "validation", "train"} for row in rows)
    out_dir = tmp_path / "datasets" / "generative_training" / performance_id / run_id
    assert out_dir.exists()


def test_quality_score_penalizes_low_reliability(tmp_path: Path, monkeypatch) -> None:
    manifest, _, _ = _setup_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    jsonl_path, _, _ = build_generative_training_examples(manifest)
    rows = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_target = {f"{row['target_start_seconds']}-{row['target_end_seconds']}": row for row in rows if row["task_type"] == "continuation"}
    high = by_target["10.0-20.0"]["quality_score"]["final_score"]
    low = by_target["30.0-40.0"]["quality_score"]["final_score"] if "30.0-40.0" in by_target else 0.0
    assert high > low


def test_missing_external_witness_does_not_force_exclude(tmp_path: Path, monkeypatch) -> None:
    manifest, performance_id, run_id = _setup_workspace(tmp_path)
    feature_dir = tmp_path / "features" / "performances" / performance_id / run_id / "external_model_features"
    for filename in ("essentia_features.json", "music21_features.json", "model_consensus.json", "model_witness_comparison.json"):
        path = feature_dir / filename
        if path.exists():
            path.unlink()
    monkeypatch.chdir(tmp_path)
    jsonl_path, _, _ = build_generative_training_examples(manifest)
    rows = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert any("missing_external_witness_refs" in row.get("split_reason_codes", []) for row in rows)
    assert any(row["split_recommendation"] in {"review", "validation", "train"} for row in rows)


def test_diagnostics_outputs_split_reasons(tmp_path: Path, monkeypatch) -> None:
    manifest, performance_id, run_id = _setup_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    build_generative_training_examples(manifest)
    dataset_dir = tmp_path / "datasets" / "generative_training" / performance_id / run_id
    json_path, md_path = diagnose_generative_examples(dataset_dir)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert json_path.exists()
    assert md_path.exists()
    assert "split_reason_breakdown" in payload
    assert "quality_component_stats" in payload
    assert "per_task_stats" in payload


def test_long_form_continuation_uses_two_window_context(tmp_path: Path, monkeypatch) -> None:
    manifest, _, _ = _setup_workspace(tmp_path, long_form=True)
    monkeypatch.chdir(tmp_path)
    jsonl_path, _, _ = build_generative_training_examples(manifest)
    rows = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    continuation = [row for row in rows if row["task_type"] == "continuation"]
    assert continuation
    assert any("long_form_two_window_context" in row.get("limitations", []) for row in continuation)


def test_conservative_routing_with_pitch_harmony_evidence_allows_harmony(tmp_path: Path, monkeypatch) -> None:
    manifest, _, _ = _setup_workspace(tmp_path, conservative_routing=True)
    monkeypatch.chdir(tmp_path)
    jsonl_path, _, _ = build_generative_training_examples(manifest)
    rows = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    harmony_rows = [row for row in rows if row["task_type"] == "harmony_continuation"]
    assert harmony_rows
    assert any("harmony_evidence_overlap" in row.get("limitations", []) for row in harmony_rows)


def test_call_response_policy_does_not_require_hard_vocal_label() -> None:
    assert _task_allowed("call_response", "rhythm_dominant", has_response_evidence=True)


def test_phrase_boundary_evidence_present_in_quality_breakdown(tmp_path: Path, monkeypatch) -> None:
    manifest, _, _ = _setup_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    jsonl_path, _, _ = build_generative_training_examples(manifest)
    row = json.loads(next(line for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()))
    breakdown = row.get("quality_component_breakdown", {})
    assert "phrase_boundary_evidence" in breakdown
    assert "phrase_boundary_evidence_components" in breakdown


def test_pairing_diagnostics_reports_near_threshold_examples(tmp_path: Path, monkeypatch) -> None:
    manifest, performance_id, run_id = _setup_workspace(tmp_path, long_form=True)
    monkeypatch.chdir(tmp_path)
    build_generative_training_examples(manifest)
    dataset_dir = tmp_path / "datasets" / "generative_training" / performance_id / run_id
    json_path, md_path = diagnose_generative_pairing(dataset_dir)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert md_path.exists()
    assert "examples_just_below_train_threshold" in payload
    assert "examples_just_below_validation_threshold" in payload


def test_long_form_fixture_yields_validation_without_threshold_drop(tmp_path: Path, monkeypatch) -> None:
    manifest, _, _ = _setup_workspace(tmp_path, long_form=True, review_required=False)
    monkeypatch.chdir(tmp_path)
    jsonl_path, _, _ = build_generative_training_examples(manifest)
    rows = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    validation_count = sum(1 for row in rows if row.get("split_recommendation") == "validation")
    exclude_count = sum(1 for row in rows if row.get("split_recommendation") == "exclude")
    assert validation_count > 0
    assert exclude_count <= max(2, len(rows) // 10)


def test_validator_rejects_missing_refs_and_huge_arrays(tmp_path: Path, monkeypatch) -> None:
    manifest, performance_id, run_id = _setup_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    jsonl_path, _, _ = build_generative_training_examples(manifest)
    rows = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows[0]["target_midi_ref"] = None
    rows[0]["target_representation"]["pitch_tokens"] = [f"n{x}" for x in range(400)]
    rows[0]["split_recommendation"] = "bad_split"
    jsonl_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    dataset_dir = tmp_path / "datasets" / "generative_training" / performance_id / run_id
    result = validate_generative_training_examples(dataset_dir)
    assert result["status"] == "failed"
    assert any("target_midi_ref" in err for err in result["errors"])
    assert any("huge embedded arrays" in err for err in result["errors"])
    assert any("invalid split_recommendation" in err for err in result["errors"])

