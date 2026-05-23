from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

CORE_GENERATIVE_TASKS = {
    "continuation",
    "phrase_continuation",
    "groove_continuation",
    "harmony_continuation",
    "melody_continuation",
    "call_response",
    "motif_transformation",
    "section_transition",
    "buildup_to_release",
    "infill_missing_region",
}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:  # noqa: BLE001
        return fallback


def _pct(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100.0, 4)


def _per_minute(count: float, duration_seconds: float) -> float:
    if duration_seconds <= 0:
        return 0.0
    return round((count / duration_seconds) * 60.0, 6)


def _count_non_empty(records: list[dict[str, Any]], field: str) -> int:
    count = 0
    for row in records:
        value = row.get(field)
        if value is None:
            continue
        if isinstance(value, (list, dict, str)) and len(value) == 0:
            continue
        count += 1
    return count


def _average_evidence_refs(records: list[dict[str, Any]]) -> float:
    if not records:
        return 0.0
    total = 0
    for row in records:
        refs = row.get("evidence_refs")
        if isinstance(refs, list):
            total += len(refs)
    return round(total / max(1, len(records)), 6)


def _domain_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    output = {
        "rhythm_time": 0,
        "pitch_harmony": 0,
        "midi_observations": 0,
        "routing_content_state": 0,
        "external_witness_refs": 0,
    }
    for row in records:
        if any(name in row for name in ("local_tempo_bpm", "subdivision_type", "meter_time_refs", "pulse_stability")):
            output["rhythm_time"] += 1
        if any(
            name in row
            for name in (
                "pitch_class_summary",
                "interval_class_summary",
                "sonority_type_candidate",
                "voice_leading_summary",
                "counterpoint_summary",
                "tuning_summary",
            )
        ):
            output["pitch_harmony"] += 1
        if any(name in row for name in ("pitch_range", "note_count", "note_density_per_second", "start_seconds", "end_seconds")):
            output["midi_observations"] += 1
        if "content_state" in row:
            output["routing_content_state"] += 1
        if isinstance(row.get("external_feature_refs"), dict):
            output["external_witness_refs"] += 1
    return output


def _provider_status(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"present": False, "status": "missing"}
    payload = _read_json(path)
    status = str(payload.get("status", "unknown"))
    return {"present": status == "success", "status": status}


def _resolve_duration(perf_manifest: dict[str, Any], segments_manifest_path: Path, source_records: list[dict[str, Any]]) -> float:
    duration_seconds = _safe_float(perf_manifest.get("duration_seconds"), 0.0)
    if duration_seconds > 0:
        return duration_seconds
    if segments_manifest_path.exists():
        segments_manifest = _read_json(segments_manifest_path)
        duration_seconds = _safe_float(segments_manifest.get("duration_seconds"), 0.0)
        if duration_seconds > 0:
            return duration_seconds
    max_end = 0.0
    for row in source_records:
        end_seconds = _safe_float(row.get("end_seconds"), 0.0)
        if end_seconds > max_end:
            max_end = end_seconds
    return round(max_end, 6)


def _index_performance_manifests(project_root: Path) -> dict[str, Path]:
    output: dict[str, Path] = {}
    for path in sorted((project_root / "performances" / "library").glob("**/performance_manifest.json")):
        payload = _read_json(path)
        performance_id = str(payload.get("performance_id", path.parent.name))
        output[performance_id] = path
    return output


def _token_overlap_score(a: str, b: str) -> int:
    a_tokens = {token for token in a.split("_") if token}
    b_tokens = {token for token in b.split("_") if token}
    return len(a_tokens & b_tokens)


def _resolve_generative_dataset_dir(project_root: Path, performance_id: str, run_id: str) -> Path:
    direct = (project_root / "datasets" / "generative_training" / performance_id / run_id).resolve()
    if (direct / "generative_manifest.json").exists():
        return direct

    root = (project_root / "datasets" / "generative_training").resolve()
    if not root.exists():
        return direct
    candidates = [path.parent for path in root.glob(f"*/{run_id}/generative_manifest.json")]
    if not candidates:
        return direct
    if len(candidates) == 1:
        return candidates[0]

    ranked = sorted(
        candidates,
        key=lambda path: (
            _token_overlap_score(performance_id, path.parent.name),
            int(path.parent.name.startswith(performance_id.split("_", 1)[0])),
            len(path.parent.name),
        ),
        reverse=True,
    )
    return ranked[0]


def audit_dataset_quality_yield(
    *,
    project_root: Path = Path("."),
    exports_root: Path = Path("datasets") / "training_exports",
    features_root: Path = Path("features") / "performances",
    output_dir: Path = Path("reports") / "dataset_quality",
) -> tuple[Path, Path]:
    project_root = project_root.resolve()
    exports_root = (project_root / exports_root).resolve()
    features_root = (project_root / features_root).resolve()
    output_dir = (project_root / output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    perf_manifest_index = _index_performance_manifests(project_root)

    export_manifest_paths = sorted(exports_root.glob("**/export_manifest.json"))
    feature_manifest_paths = sorted(features_root.glob("**/feature_pack_manifest.json"))

    key_to_export_manifest: dict[tuple[str, str], Path] = {}
    key_to_feature_manifest: dict[tuple[str, str], Path] = {}
    feature_paths_by_perf: defaultdict[str, set[str]] = defaultdict(set)
    export_paths_by_perf: defaultdict[str, set[str]] = defaultdict(set)

    for path in export_manifest_paths:
        payload = _read_json(path)
        performance_id = str(payload.get("performance_id", path.parent.parent.name))
        run_id = str(payload.get("segment_run_id", path.parent.name))
        key_to_export_manifest[(performance_id, run_id)] = path
        export_paths_by_perf[performance_id].add(path.parent.parent.as_posix())

    for path in feature_manifest_paths:
        payload = _read_json(path)
        performance_id = str(payload.get("performance_id", path.parent.parent.name))
        run_id = str(payload.get("segment_run_id", path.parent.name))
        key_to_feature_manifest[(performance_id, run_id)] = path
        feature_paths_by_perf[performance_id].add(path.parent.parent.as_posix())

    all_keys = sorted(set(key_to_export_manifest.keys()) | set(key_to_feature_manifest.keys()))

    performances: list[dict[str, Any]] = []
    dataset_risk_flags: Counter[str] = Counter()
    dataset_blockers: Counter[str] = Counter()
    missing_provider_counts: Counter[str] = Counter()
    records_per_minute_values: list[float] = []
    accepted_per_minute_values: list[float] = []
    review_per_minute_values: list[float] = []
    generative_task_counts: Counter[str] = Counter()
    generative_quality_by_task: defaultdict[str, list[float]] = defaultdict(list)
    generative_split_counts: Counter[str] = Counter()
    total_generative_examples = 0
    total_generative_train = 0
    total_generative_validation = 0
    total_generative_review = 0
    total_generative_exclude = 0

    for performance_id, run_id in all_keys:
        export_manifest_path = key_to_export_manifest.get((performance_id, run_id))
        feature_manifest_path = key_to_feature_manifest.get((performance_id, run_id))
        export_manifest = _read_json(export_manifest_path) if export_manifest_path else {}
        feature_manifest = _read_json(feature_manifest_path) if feature_manifest_path else {}
        feature_dir = feature_manifest_path.parent if feature_manifest_path else Path(str(export_manifest.get("source_feature_pack_path", "")))
        export_dir = export_manifest_path.parent if export_manifest_path else None

        perf_manifest_path = perf_manifest_index.get(performance_id)
        perf_manifest = _read_json(perf_manifest_path) if perf_manifest_path else {}
        segments_manifest_path = Path(str(perf_manifest.get("active_segments_manifest_path", ""))).resolve() if perf_manifest else Path("")
        merged_midi_path = Path(str(perf_manifest.get("active_merged_midi_path", ""))).resolve() if perf_manifest else Path("")

        source_records = _read_jsonl(feature_dir / "ai_training_records.jsonl") if feature_dir and feature_dir.exists() else []
        accepted_records = _read_jsonl(export_dir / "accepted_records.jsonl") if export_dir else []
        weak_records = _read_jsonl(export_dir / "weak_label_records.jsonl") if export_dir else []
        review_records = _read_jsonl(export_dir / "review_required_records.jsonl") if export_dir else []
        quarantined_records = _read_jsonl(export_dir / "quarantined_records.jsonl") if export_dir else []

        duration_seconds = _resolve_duration(perf_manifest, segments_manifest_path, source_records)
        source_count = int(export_manifest.get("source_ai_record_count", len(source_records)) or 0)
        accepted_count = int(export_manifest.get("accepted_observation_count", len(accepted_records)) or 0)
        weak_count = int(export_manifest.get("weak_label_count", len(weak_records)) or 0)
        review_count = int(export_manifest.get("review_required_count", len(review_records)) or 0)
        quarantined_count = int(export_manifest.get("quarantined_count", len(quarantined_records)) or 0)

        records_per_minute = _per_minute(source_count, duration_seconds)
        accepted_per_minute = _per_minute(accepted_count, duration_seconds)
        weak_per_minute = _per_minute(weak_count, duration_seconds)
        review_pct = _pct(review_count, source_count)

        records_per_minute_values.append(records_per_minute)
        accepted_per_minute_values.append(accepted_per_minute)
        review_per_minute_values.append(_per_minute(review_count, duration_seconds))

        external_dir = feature_dir / "external_model_features"
        trust_dir = feature_dir / "trust"
        routing_dir = feature_dir / "routing"
        rhythm_path = feature_dir / "rhythm_features.json"
        harmony_path = feature_dir / "harmony_features.json"
        meter_path = feature_dir / "rhythm_time" / "meter_time_features.json"
        pitch_path = feature_dir / "pitch_harmony" / "pitch_harmony_features.json"
        quality_path = trust_dir / "quality_gates.json"
        reliability_path = trust_dir / "transcription_reliability.json"
        audit_path = trust_dir / "training_data_audit.json"
        consensus_path = external_dir / "model_consensus.json"

        routing_payload = _read_json(routing_dir / "content_region_routes.json")
        meter_payload = _read_json(meter_path)
        pitch_payload = _read_json(pitch_path)
        consensus_payload = _read_json(consensus_path)
        comparison_payload = _read_json(external_dir / "model_witness_comparison.json")
        trust_audit_payload = _read_json(audit_path)
        generative_dir = _resolve_generative_dataset_dir(project_root, performance_id, run_id)
        generative_manifest = _read_json(generative_dir / "generative_manifest.json")
        generative_examples = _read_jsonl(generative_dir / "generative_examples.jsonl")

        content_state_counts = routing_payload.get("content_state_counts", {})
        if not isinstance(content_state_counts, dict):
            content_state_counts = {}

        layer_completeness = {
            "source_manifest_present": bool(perf_manifest_path and perf_manifest_path.exists()),
            "segments_present": bool(segments_manifest_path and segments_manifest_path.exists()),
            "merged_midi_present": bool(merged_midi_path and merged_midi_path.exists()),
            "rhythm_features_present": rhythm_path.exists(),
            "harmony_features_present": harmony_path.exists(),
            "routing_present": (routing_dir / "content_region_routes.json").exists(),
            "meter_time_present": meter_path.exists(),
            "pitch_harmony_present": pitch_path.exists(),
            "trust_reports_present": quality_path.exists() and reliability_path.exists(),
            "training_export_present": bool(export_manifest_path and export_manifest_path.exists()),
            "external_witnesses_present": any((external_dir / name).exists() for name in ("essentia_features.json", "music21_features.json", "musicnn_features.json", "beat_tracker_features.json", "omnizart_availability.json")),
            "model_consensus_present": consensus_path.exists(),
            "audit_report_present": audit_path.exists(),
        }

        evidence_density = {
            "average_evidence_refs_per_record": _average_evidence_refs(source_records),
            "percent_records_with_confidence": _pct(_count_non_empty(source_records, "confidence"), len(source_records)),
            "percent_records_with_limitations": _pct(_count_non_empty(source_records, "limitations"), len(source_records)),
            "percent_records_with_model_source_refs": _pct(_count_non_empty(source_records, "model_source_refs"), len(source_records)),
            "percent_records_with_theory_source_refs": _pct(_count_non_empty(source_records, "theory_source_refs"), len(source_records)),
            "percent_records_with_content_state": _pct(_count_non_empty(source_records, "content_state"), len(source_records)),
            "percent_records_with_external_feature_refs": _pct(_count_non_empty(source_records, "external_feature_refs"), len(source_records)),
            "percent_records_with_consensus_refs": _pct(_count_non_empty(source_records, "consensus_refs"), len(source_records)),
        }

        accepted_domain_counts = _domain_counts(accepted_records)
        weak_domain_counts = _domain_counts(weak_records)
        review_domain_counts = _domain_counts(review_records)
        labels_suppressed_by_routing = int(
            trust_audit_payload.get("routing_and_label_upgrade_readiness", {}).get("labels_suppressed_by_routing", 0)
            if isinstance(trust_audit_payload.get("routing_and_label_upgrade_readiness"), dict)
            else 0
        )
        upgrade_candidates = int(
            trust_audit_payload.get("routing_and_label_upgrade_readiness", {}).get("upgrade_candidates", 0)
            if isinstance(trust_audit_payload.get("routing_and_label_upgrade_readiness"), dict)
            else 0
        )
        downgrade_or_suppress_candidates = int(
            trust_audit_payload.get("routing_and_label_upgrade_readiness", {}).get("downgrade_or_suppress_candidates", 0)
            if isinstance(trust_audit_payload.get("routing_and_label_upgrade_readiness"), dict)
            else 0
        )
        trust_quality = {
            "ratios": {
                "accepted_ratio_pct": _pct(accepted_count, source_count),
                "weak_ratio_pct": _pct(weak_count, source_count),
                "review_ratio_pct": _pct(review_count, source_count),
                "quarantine_ratio_pct": _pct(quarantined_count, source_count),
            },
            "accepted_fields_by_domain": accepted_domain_counts,
            "weak_labels_by_domain": weak_domain_counts,
            "review_required_labels_by_domain": review_domain_counts,
            "labels_suppressed_by_routing": labels_suppressed_by_routing,
            "upgrade_candidates": upgrade_candidates,
            "downgrade_or_suppress_candidates": downgrade_or_suppress_candidates,
        }

        essentia_status = _provider_status(external_dir / "essentia_features.json")
        music21_status = _provider_status(external_dir / "music21_features.json")
        musicnn_status = _provider_status(external_dir / "musicnn_features.json")
        beat_status = _provider_status(external_dir / "beat_tracker_features.json")
        omnizart_status = _provider_status(external_dir / "omnizart_availability.json")

        for provider_name, provider_payload in (
            ("musicnn", musicnn_status),
            ("beat_tracker", beat_status),
            ("omnizart", omnizart_status),
        ):
            if provider_payload["status"] in {"missing", "unavailable", "failed", "unknown"}:
                missing_provider_counts[provider_name] += 1

        unresolved_conflicts = consensus_payload.get("unresolved_conflicts", [])
        if not isinstance(unresolved_conflicts, list):
            unresolved_conflicts = []
        confidence_penalties = consensus_payload.get("confidence_penalties", [])
        if not isinstance(confidence_penalties, list):
            confidence_penalties = []
        witness_coverage = {
            "yourmt3_pretty_midi_present": bool(merged_midi_path and merged_midi_path.exists()),
            "librosa_internal_features_present": rhythm_path.exists() and harmony_path.exists(),
            "essentia": essentia_status,
            "music21": music21_status,
            "musicnn": musicnn_status,
            "beatnet_madmom": beat_status,
            "omnizart": omnizart_status,
            "consensus_status": str(consensus_payload.get("consensus_status", "missing")) if consensus_payload else "missing",
            "unresolved_conflicts": unresolved_conflicts,
            "low_confidence_warnings": [str(item) for item in confidence_penalties if isinstance(item, str)],
        }

        beat_meter_hypotheses = meter_payload.get("beat_meter_hypotheses", [])
        if not isinstance(beat_meter_hypotheses, list):
            beat_meter_hypotheses = []
        pitch_hypotheses = 0
        for key in ("interval_analysis", "melody_contour", "harmony_sonority", "chord_movement", "counterpoint", "tuning_system"):
            payload = pitch_payload.get(key, [])
            if isinstance(payload, list):
                pitch_hypotheses += len(payload)

        tuning_records = pitch_payload.get("tuning_system", [])
        if not isinstance(tuning_records, list):
            tuning_records = []
        microtonal_available = any(bool(item.get("microtonal_analysis_available")) for item in tuning_records if isinstance(item, dict))
        microtonal_limitations = [
            limitation
            for row in tuning_records
            if isinstance(row, dict)
            for limitation in (row.get("limitations", []) if isinstance(row.get("limitations"), list) else [])
            if isinstance(limitation, str)
        ]
        musical_coverage = {
            "content_state_counts": content_state_counts,
            "meter_time_hypothesis_coverage": len(beat_meter_hypotheses),
            "pitch_harmony_hypothesis_coverage": pitch_hypotheses,
            "rhythm_cycle_phrase_macro_features_present": bool(
                isinstance(meter_payload.get("cycle_pattern_records"), list)
                and isinstance(meter_payload.get("phrase_rhythm_records"), list)
                and isinstance(meter_payload.get("macro_time_records"), list)
            ),
            "interval_melody_counterpoint_tuning_present": {
                "interval_analysis": isinstance(pitch_payload.get("interval_analysis"), list),
                "melody_contour": isinstance(pitch_payload.get("melody_contour"), list),
                "counterpoint": isinstance(pitch_payload.get("counterpoint"), list),
                "tuning_system": isinstance(pitch_payload.get("tuning_system"), list),
            },
            "microtonal_analysis_availability": microtonal_available,
            "microtonal_limitations": microtonal_limitations[:8],
            "experimental_ambiguous_harmony_handling": any(
                isinstance(row, dict) and _safe_float(row.get("ambiguity"), 0.0) >= 0.6
                for row in (pitch_payload.get("harmony_sonority", []) if isinstance(pitch_payload.get("harmony_sonority"), list) else [])
            ),
        }

        risk_flags: list[str] = []
        content_total = sum(int(value) for value in content_state_counts.values() if isinstance(value, (int, float)))
        silence_count = int(content_state_counts.get("silence_or_noise", 0) or 0)
        if content_total > 0 and (silence_count / max(1, content_total)) >= 0.45:
            risk_flags.append("too_many_silence_or_noise_regions")
        pitch_evidence_present = bool(_count_non_empty(source_records, "pitch_class_summary") or _count_non_empty(source_records, "pitch_range"))
        harmonic_states = int(content_state_counts.get("harmonic_dominant", 0) or 0) + int(content_state_counts.get("polyphonic_full_mix", 0) or 0)
        if pitch_evidence_present and harmonic_states == 0:
            risk_flags.append("zero_harmonic_or_full_mix_states_with_pitch_evidence")
        beat_confidence = _safe_float(
            _read_json(external_dir / "essentia_features.json").get("rhythm_descriptors", {}).get("beat_confidence")
            if (external_dir / "essentia_features.json").exists()
            else None,
            0.0,
        )
        if essentia_status["present"] and beat_confidence > 0 and beat_confidence < 0.5:
            risk_flags.append("low_beat_confidence")
        if beat_status["status"] in {"missing", "unavailable", "failed"}:
            risk_flags.append("missing_external_meter_witness")
        if not microtonal_available:
            risk_flags.append("missing_microtonal_evidence")
        if review_pct >= 60.0:
            risk_flags.append("high_review_required_percentage")
        weak_without_evidence = sum(
            1
            for row in weak_records
            if not isinstance(row.get("evidence_refs"), list) or len(row.get("evidence_refs", [])) == 0
        )
        if weak_without_evidence > 0:
            risk_flags.append("weak_labels_without_evidence")
        hard_without_conf = sum(
            1
            for row in accepted_records
            if str(row.get("label_status", "")) in {"raw_observation", "derived_observation", "human_verified_label"}
            and row.get("confidence") is None
        )
        if hard_without_conf > 0:
            risk_flags.append("hard_labels_without_confidence")
        disagreements = consensus_payload.get("disagreements", [])
        if isinstance(disagreements, list) and disagreements:
            risk_flags.append("external_witness_disagreement")
        if len(feature_paths_by_perf.get(performance_id, set())) > 1 or len(export_paths_by_perf.get(performance_id, set())) > 1:
            risk_flags.append("duplicate_legacy_compact_paths")
        if not export_manifest_path:
            risk_flags.append("missing_exports")
        task_counts = generative_manifest.get("examples_by_task_type", {})
        if not isinstance(task_counts, dict):
            task_counts = {}
        split_counts = generative_manifest.get("split_counts", {})
        if not isinstance(split_counts, dict):
            split_counts = {}
        missing_generative_task_coverage = sorted(task for task in CORE_GENERATIVE_TASKS if int(task_counts.get(task, 0) or 0) <= 0)
        if missing_generative_task_coverage:
            risk_flags.append("missing_generative_task_coverage")

        for flag in risk_flags:
            dataset_risk_flags[flag] += 1

        ready_for_observation_only = (
            accepted_count > 0
            and review_pct < 55.0
            and "missing_exports" not in risk_flags
            and "hard_labels_without_confidence" not in risk_flags
            and "high_review_required_percentage" not in risk_flags
        )
        needs_review = "external_witness_disagreement" in risk_flags or "high_review_required_percentage" in risk_flags
        needs_external_witness = (not essentia_status["present"]) or (not music21_status["present"])
        needs_routing_calibration = any(flag in risk_flags for flag in ("too_many_silence_or_noise_regions", "zero_harmonic_or_full_mix_states_with_pitch_evidence"))
        needs_meter_calibration = "low_beat_confidence" in risk_flags or len(beat_meter_hypotheses) == 0
        needs_pitch_harmony_calibration = pitch_hypotheses == 0 or "external_witness_disagreement" in risk_flags
        needs_manual_review = review_pct >= 60.0 or "external_witness_disagreement" in risk_flags
        good_mass_template = ready_for_observation_only and not needs_external_witness and not needs_manual_review

        recommendations = {
            "ready_for_training_observation_only": ready_for_observation_only,
            "needs_review": needs_review,
            "needs_external_witness": needs_external_witness,
            "needs_routing_calibration": needs_routing_calibration,
            "needs_meter_calibration": needs_meter_calibration,
            "needs_pitch_harmony_calibration": needs_pitch_harmony_calibration,
            "needs_manual_review": needs_manual_review,
            "good_candidate_for_mass_ingestion_template": good_mass_template,
        }

        for blocker, enabled in recommendations.items():
            if enabled and blocker in {
                "needs_external_witness",
                "needs_routing_calibration",
                "needs_meter_calibration",
                "needs_pitch_harmony_calibration",
                "needs_manual_review",
            }:
                dataset_blockers[blocker] += 1

        average_quality_score = _safe_float(generative_manifest.get("average_quality_score"), 0.0)
        examples_per_minute = _safe_float(generative_manifest.get("examples_per_minute"), 0.0)
        high_quality_examples_per_minute = _safe_float(generative_manifest.get("high_quality_examples_per_minute"), 0.0)
        weakest_task_domains = sorted(
            {
                str(example.get("task_type"))
                for example in generative_examples
                if isinstance(example, dict) and _safe_float(example.get("quality_score", {}).get("final_score"), 0.0) < 0.45
            }
        )
        strongest_task_domains = sorted(
            {
                str(example.get("task_type"))
                for example in generative_examples
                if isinstance(example, dict) and _safe_float(example.get("quality_score", {}).get("final_score"), 0.0) >= 0.72
            }
        )
        for task_name, count in task_counts.items():
            generative_task_counts[str(task_name)] += int(count or 0)
        for split_name, count in split_counts.items():
            generative_split_counts[str(split_name)] += int(count or 0)
        for example in generative_examples:
            if not isinstance(example, dict):
                continue
            task_name = str(example.get("task_type", "unknown"))
            score = _safe_float(example.get("quality_score", {}).get("final_score"), 0.0)
            generative_quality_by_task[task_name].append(score)
        total_generative_examples += int(generative_manifest.get("generative_examples_count", len(generative_examples)) or 0)
        total_generative_train += int(split_counts.get("train", 0) or 0)
        total_generative_validation += int(split_counts.get("validation", 0) or 0)
        total_generative_review += int(split_counts.get("review", 0) or 0)
        total_generative_exclude += int(split_counts.get("exclude", 0) or 0)

        performances.append(
            {
                "performance_id": performance_id,
                "segment_run_id": run_id,
                "paths": {
                    "performance_manifest": perf_manifest_path.as_posix() if perf_manifest_path else None,
                    "feature_pack_manifest": feature_manifest_path.as_posix() if feature_manifest_path else None,
                    "export_manifest": export_manifest_path.as_posix() if export_manifest_path else None,
                    "feature_dir": feature_dir.as_posix() if feature_dir else None,
                    "export_dir": export_dir.as_posix() if export_dir else None,
                },
                "basic_yield": {
                    "duration_seconds": round(duration_seconds, 6),
                    "source_ai_record_count": source_count,
                    "accepted_observation_count": accepted_count,
                    "weak_label_count": weak_count,
                    "review_required_count": review_count,
                    "quarantined_count": quarantined_count,
                    "records_per_minute": records_per_minute,
                    "accepted_observations_per_minute": accepted_per_minute,
                    "weak_labels_per_minute": weak_per_minute,
                    "review_required_percentage": review_pct,
                },
                "layer_completeness": layer_completeness,
                "evidence_density": evidence_density,
                "trust_quality": trust_quality,
                "witness_coverage": witness_coverage,
                "musical_coverage": musical_coverage,
                "risk_flags": sorted(set(risk_flags)),
                "recommendations": recommendations,
                "witness_summary": {
                    "essentia_status": essentia_status["status"],
                    "music21_status": music21_status["status"],
                    "comparison_provider_status": comparison_payload.get("provider_status", {}),
                },
                "generative_dataset": {
                    "generative_dataset_present": bool(generative_manifest),
                    "generative_dataset_path": generative_dir.as_posix() if generative_dir.exists() else None,
                    "generative_examples_count": int(generative_manifest.get("generative_examples_count", len(generative_examples)) or 0),
                    "train_recommended_count": int(split_counts.get("train", 0) or 0),
                    "validation_recommended_count": int(split_counts.get("validation", 0) or 0),
                    "review_recommended_count": int(split_counts.get("review", 0) or 0),
                    "exclude_recommended_count": int(split_counts.get("exclude", 0) or 0),
                    "examples_by_task_type": {str(k): int(v or 0) for k, v in task_counts.items()},
                    "average_quality_score": average_quality_score,
                    "examples_per_minute": examples_per_minute,
                    "high_quality_examples_per_minute": high_quality_examples_per_minute,
                    "weakest_task_domains": weakest_task_domains,
                    "strongest_task_domains": strongest_task_domains,
                    "missing_task_coverage": missing_generative_task_coverage,
                },
            }
        )

    ready_candidates = sum(
        1
        for item in performances
        if bool(item.get("recommendations", {}).get("good_candidate_for_mass_ingestion_template"))
    )
    total_performances = len(performances)
    avg_records_per_min = round(sum(records_per_minute_values) / max(1, len(records_per_minute_values)), 6)
    avg_accepted_per_min = round(sum(accepted_per_minute_values) / max(1, len(accepted_per_minute_values)), 6)
    avg_review_per_min = round(sum(review_per_minute_values) / max(1, len(review_per_minute_values)), 6)

    if missing_provider_counts:
        best_next_analyzer_to_package = missing_provider_counts.most_common(1)[0][0]
    else:
        best_next_analyzer_to_package = "none"

    minimum_blockers = [name for name, count in dataset_blockers.most_common() if count > 0]
    corpus_ready = (
        total_performances > 0
        and ready_candidates == total_performances
        and not minimum_blockers
        and dataset_risk_flags.get("missing_exports", 0) == 0
    )

    dataset_recommendations = {
        "corpus_ready_for_mass_ingestion": corpus_ready,
        "minimum_blockers_before_mass_input": minimum_blockers,
        "best_next_analyzer_to_package": best_next_analyzer_to_package,
        "expected_data_yield_per_hour": round(avg_records_per_min * 60.0, 4),
        "expected_accepted_observations_per_hour": round(avg_accepted_per_min * 60.0, 4),
        "expected_review_burden_per_hour": round(avg_review_per_min * 60.0, 4),
        "total_generative_examples_count": total_generative_examples,
        "total_generative_train_recommended_count": total_generative_train,
        "total_generative_validation_recommended_count": total_generative_validation,
        "total_generative_review_recommended_count": total_generative_review,
        "total_generative_exclude_recommended_count": total_generative_exclude,
        "generative_examples_by_task_type": dict(sorted(generative_task_counts.items())),
        "average_generative_quality_by_task_type": {
            task: round(sum(scores) / max(1, len(scores)), 6)
            for task, scores in sorted(generative_quality_by_task.items())
        },
        "missing_generative_task_coverage": sorted(task for task in CORE_GENERATIVE_TASKS if generative_task_counts.get(task, 0) <= 0),
    }

    payload = {
        "total_performances_scanned": total_performances,
        "performance_reports": performances,
        "dataset_risk_flag_counts": dict(sorted(dataset_risk_flags.items())),
        "dataset_recommendations": dataset_recommendations,
    }

    json_path = output_dir / "dataset_quality_yield_report.json"
    md_path = output_dir / "dataset_quality_yield_report.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    lines = [
        "# Dataset Quality and Yield Report",
        "",
        f"- total performances scanned: `{total_performances}`",
        f"- corpus ready for mass ingestion: `{dataset_recommendations['corpus_ready_for_mass_ingestion']}`",
        f"- minimum blockers before mass input: `{json.dumps(dataset_recommendations['minimum_blockers_before_mass_input'], ensure_ascii=True)}`",
        f"- best next analyzer to package: `{dataset_recommendations['best_next_analyzer_to_package']}`",
        f"- expected data yield per hour: `{dataset_recommendations['expected_data_yield_per_hour']}`",
        f"- expected accepted observations per hour: `{dataset_recommendations['expected_accepted_observations_per_hour']}`",
        f"- expected review burden per hour: `{dataset_recommendations['expected_review_burden_per_hour']}`",
        f"- total generative examples: `{dataset_recommendations['total_generative_examples_count']}`",
        f"- generative split counts (train/validation/review/exclude): `{[dataset_recommendations['total_generative_train_recommended_count'], dataset_recommendations['total_generative_validation_recommended_count'], dataset_recommendations['total_generative_review_recommended_count'], dataset_recommendations['total_generative_exclude_recommended_count']]}`",
        f"- missing generative task coverage: `{json.dumps(dataset_recommendations['missing_generative_task_coverage'], ensure_ascii=True)}`",
        "",
        "## Dataset risk flag counts",
    ]
    if payload["dataset_risk_flag_counts"]:
        for name, count in payload["dataset_risk_flag_counts"].items():
            lines.append(f"- {name}: `{count}`")
    else:
        lines.append("- none")
    for report in performances:
        basic = report["basic_yield"]
        lines.extend(
            [
                "",
                f"## {report['performance_id']} / {report['segment_run_id']}",
                f"- records_per_minute: `{basic['records_per_minute']}`",
                f"- accepted_observations_per_minute: `{basic['accepted_observations_per_minute']}`",
                f"- review_required_percentage: `{basic['review_required_percentage']}`",
                f"- risk_flags: `{json.dumps(report['risk_flags'], ensure_ascii=True)}`",
                f"- recommendations: `{json.dumps(report['recommendations'], ensure_ascii=True)}`",
                f"- witness_coverage: `{json.dumps(report['witness_coverage'], ensure_ascii=True)}`",
                f"- layer_completeness: `{json.dumps(report['layer_completeness'], ensure_ascii=True)}`",
                f"- generative_dataset: `{json.dumps(report.get('generative_dataset', {}), ensure_ascii=True)}`",
            ]
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path.resolve(), md_path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit dataset quality and data yield across existing feature packs and training exports.")
    parser.add_argument("--exports-root", default="datasets/training_exports", help="Root folder containing export folders")
    parser.add_argument("--features-root", default="features/performances", help="Root folder containing feature pack folders")
    parser.add_argument("--output-dir", default="reports/dataset_quality", help="Folder where report JSON/Markdown will be written")
    args = parser.parse_args()
    json_path, md_path = audit_dataset_quality_yield(
        exports_root=Path(args.exports_root),
        features_root=Path(args.features_root),
        output_dir=Path(args.output_dir),
    )
    print(f"DATASET_QUALITY_YIELD_REPORT_JSON={json_path.as_posix()}")
    print(f"DATASET_QUALITY_YIELD_REPORT_MD={md_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
