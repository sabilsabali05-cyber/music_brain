from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.feature_dataset_common import (
    ensure_windows_safe_artifact_path,
    now_iso,
    resolve_artifact_performance_dir,
    save_json,
)
from scripts.trust_common import load_jsonl_records, resolve_performance_context, trust_dir
from features.trust.field_trust_policy import (
    POLICY_VERSION,
    classify_record_for_export,
    make_accepted_observation_record,
    make_review_required_record,
    make_weak_label_record,
)
from features.model_sources import MODEL_SOURCES
from features.theory_sources import THEORY_SOURCES


def _line_dump(record: dict[str, Any]) -> str:
    return json.dumps(record, ensure_ascii=True)


def _window_reliability_map(reliability_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    windows = reliability_payload.get("windows", [])
    if not isinstance(windows, list):
        return output
    for item in windows:
        if not isinstance(item, dict):
            continue
        window_id = str(item.get("window_id", ""))
        if window_id:
            output[window_id] = item
    return output


def _routing_lookup(feature_dir: Path) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    routing_dir = feature_dir / "routing"
    source_map: dict[str, dict[str, Any]] = {}
    refs: dict[str, str] = {}
    for name in ["asset_classification.json", "content_region_routes.json", "analysis_routing_decisions.json"]:
        path = routing_dir / name
        if path.exists():
            refs[name.replace(".json", "")] = path.resolve().as_posix()
    decisions_path = routing_dir / "analysis_routing_decisions.json"
    if not decisions_path.exists():
        return source_map, refs
    payload = json.loads(decisions_path.read_text(encoding="utf-8"))
    decisions = payload.get("decisions", [])
    if not isinstance(decisions, list):
        return source_map, refs
    for item in decisions:
        if not isinstance(item, dict):
            continue
        source_record_id = str(item.get("source_record_id", "")).strip()
        if source_record_id:
            source_map[source_record_id] = item
    return source_map, refs


def _upgrade_lookup(feature_dir: Path) -> tuple[dict[str, list[dict[str, Any]]], str | None]:
    trust_path = feature_dir / "trust" / "label_upgrade_candidates.json"
    if not trust_path.exists():
        return {}, None
    payload = json.loads(trust_path.read_text(encoding="utf-8"))
    candidates = payload.get("candidates", [])
    if not isinstance(candidates, list):
        return {}, trust_path.resolve().as_posix()
    output: dict[str, list[dict[str, Any]]] = {}
    for item in candidates:
        if not isinstance(item, dict):
            continue
        source_label_id = str(item.get("source_label_id", "")).strip()
        if not source_label_id:
            continue
        output.setdefault(source_label_id, []).append(
            {
                "candidate_id": item.get("candidate_id"),
                "recommended_label_status": item.get("recommended_label_status"),
                "route_content_state": item.get("route_content_state"),
            }
        )
    return output, trust_path.resolve().as_posix()


def _meter_time_lookup(feature_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], str | None]:
    meter_path = feature_dir / "rhythm_time" / "meter_time_features.json"
    if not meter_path.exists():
        return [], [], [], [], None
    payload = json.loads(meter_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return [], [], [], [], meter_path.resolve().as_posix()
    micro = payload.get("microtiming_records", [])
    grid = payload.get("subdivision_grid_records", [])
    macro = payload.get("macro_time_records", [])
    meter = payload.get("beat_meter_hypotheses", [])
    return (
        [item for item in micro if isinstance(item, dict)],
        [item for item in grid if isinstance(item, dict)],
        [item for item in macro if isinstance(item, dict)],
        [item for item in meter if isinstance(item, dict)],
        meter_path.resolve().as_posix(),
    )


def _match_interval(
    rows: list[dict[str, Any]],
    *,
    start_seconds: float,
    end_seconds: float,
) -> dict[str, Any]:
    best: dict[str, Any] = {}
    best_overlap = -1.0
    for row in rows:
        row_start = float(row.get("start_seconds", start_seconds) or start_seconds)
        row_end = float(row.get("end_seconds", row_start) or row_start)
        overlap = max(0.0, min(end_seconds, row_end) - max(start_seconds, row_start))
        if overlap > best_overlap:
            best_overlap = overlap
            best = row
    return best


def _meter_time_view(
    record: dict[str, Any],
    *,
    micro_rows: list[dict[str, Any]],
    grid_rows: list[dict[str, Any]],
    macro_rows: list[dict[str, Any]],
    meter_hypotheses: list[dict[str, Any]],
    meter_path: str | None,
) -> dict[str, Any]:
    start_seconds = float(record.get("start_seconds", 0.0) or 0.0)
    end_seconds = float(record.get("end_seconds", start_seconds) or start_seconds)
    micro = _match_interval(micro_rows, start_seconds=start_seconds, end_seconds=end_seconds) if micro_rows else {}
    grid = _match_interval(grid_rows, start_seconds=start_seconds, end_seconds=end_seconds) if grid_rows else {}
    macro = _match_interval(macro_rows, start_seconds=start_seconds, end_seconds=end_seconds) if macro_rows else {}
    top_hypothesis = meter_hypotheses[0] if meter_hypotheses else {}
    if not any([micro, grid, macro, top_hypothesis, meter_path]):
        return {}
    return {
        "local_tempo_bpm": micro.get("local_tempo_bpm", grid.get("local_tempo_bpm")),
        "grid_confidence": grid.get("grid_confidence"),
        "subdivision_type": grid.get("subdivision_type"),
        "pulse_stability": micro.get("pulse_stability"),
        "microtiming_summary": micro.get("microtiming_summary"),
        "macro_section_candidate": macro.get("macro_section_candidate"),
        "meter_time_ambiguity": top_hypothesis.get("ambiguity"),
        "meter_time_refs": {
            "meter_time_features_path": meter_path,
            "micro_record_id": micro.get("record_id"),
            "grid_record_id": grid.get("record_id"),
            "macro_record_id": macro.get("macro_id"),
            "meter_hypothesis_id": top_hypothesis.get("hypothesis_id"),
        },
        "meter_hypothesis_candidates": [
            {
                "meter": item.get("meter"),
                "confidence": item.get("confidence"),
                "ambiguity": item.get("ambiguity"),
            }
            for item in meter_hypotheses[:3]
        ],
    }


def _git_commit() -> str | None:
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        return result.stdout.strip() or None
    except Exception:  # noqa: BLE001
        return None


def export_training_dataset_splits(performance_manifest_path: Path) -> Path:
    ctx = resolve_performance_context(performance_manifest_path)
    feature_dir = ctx["feature_dir"]
    trust_output_dir = trust_dir(feature_dir)
    ai_path = feature_dir / "ai_training_records.jsonl"
    pitch_harmony_path = feature_dir / "pitch_harmony" / "pitch_harmony_features.json"
    quality_path = trust_output_dir / "quality_gates.json"
    reliability_path = trust_output_dir / "transcription_reliability.json"
    ai_records = load_jsonl_records(ai_path)
    pitch_harmony_payload = json.loads(pitch_harmony_path.read_text(encoding="utf-8")) if pitch_harmony_path.exists() else {}
    quality_payload = json.loads(quality_path.read_text(encoding="utf-8")) if quality_path.exists() else {}
    reliability_payload = json.loads(reliability_path.read_text(encoding="utf-8")) if reliability_path.exists() else {}
    window_rel = _window_reliability_map(reliability_payload if isinstance(reliability_payload, dict) else {})
    overall_status = str(quality_payload.get("overall_quality_status", "review_required"))
    routing_by_source, routing_refs = _routing_lookup(feature_dir)
    upgrade_by_source, upgrade_refs_path = _upgrade_lookup(feature_dir)
    meter_micro_rows, meter_grid_rows, meter_macro_rows, meter_hypotheses, meter_path = _meter_time_lookup(feature_dir)
    external_dir = feature_dir / "external_model_features"
    external_feature_refs = {
        "essentia_features": (external_dir / "essentia_features.json").resolve().as_posix() if (external_dir / "essentia_features.json").exists() else None,
        "musicnn_features": (external_dir / "musicnn_features.json").resolve().as_posix() if (external_dir / "musicnn_features.json").exists() else None,
        "beat_tracker_features": (external_dir / "beat_tracker_features.json").resolve().as_posix() if (external_dir / "beat_tracker_features.json").exists() else None,
        "music21_features": (external_dir / "music21_features.json").resolve().as_posix() if (external_dir / "music21_features.json").exists() else None,
        "omnizart_availability": (external_dir / "omnizart_availability.json").resolve().as_posix() if (external_dir / "omnizart_availability.json").exists() else None,
    }
    model_consensus_ref = (external_dir / "model_consensus.json").resolve().as_posix() if (external_dir / "model_consensus.json").exists() else None
    model_consensus_payload = {}
    if model_consensus_ref:
        try:
            model_consensus_payload = json.loads((external_dir / "model_consensus.json").read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            model_consensus_payload = {}
    witness_agreement_summary = model_consensus_payload.get("agreements", []) if isinstance(model_consensus_payload.get("agreements"), list) else []
    witness_conflict_warnings = model_consensus_payload.get("disagreements", []) if isinstance(model_consensus_payload.get("disagreements"), list) else []
    witness_review_recommendations = (
        model_consensus_payload.get("recommended_review_items", [])
        if isinstance(model_consensus_payload.get("recommended_review_items"), list)
        else []
    )
    model_source_refs = [str(item.get("provider_id")) for item in MODEL_SOURCES if str(item.get("implementation_status")) in {"existing", "optional_adapter", "planned", "dataset_reference"}]
    theory_source_refs = [str(item.get("source_id")) for item in THEORY_SOURCES]
    available_external_witnesses = sorted([name for name, path in external_feature_refs.items() if path])
    missing_external_witnesses = sorted([name for name, path in external_feature_refs.items() if not path])

    export_root = resolve_artifact_performance_dir(Path("datasets") / "training_exports", str(ctx["performance_id"])) / ctx["segment_run_id"]
    ensure_windows_safe_artifact_path(
        export_root / "review_required_records.jsonl",
        context="training export artifact path",
    )
    export_root.mkdir(parents=True, exist_ok=True)

    split_records: dict[str, list[dict[str, Any]]] = {
        "accepted_records": [],
        "weak_label_records": [],
        "audio_midi_only_records": [],
        "review_required_records": [],
        "quarantined_records": [],
    }

    excluded_field_summary: dict[str, int] = {}
    pitch_harmony_ref = pitch_harmony_path.resolve().as_posix() if pitch_harmony_path.exists() else None
    pitch_observations = pitch_harmony_payload.get("pitch_observations", []) if isinstance(pitch_harmony_payload, dict) else []
    interval_analysis = pitch_harmony_payload.get("interval_analysis", []) if isinstance(pitch_harmony_payload, dict) else []
    sonority_records = pitch_harmony_payload.get("harmony_sonority", []) if isinstance(pitch_harmony_payload, dict) else []
    movement_records = pitch_harmony_payload.get("chord_movement", []) if isinstance(pitch_harmony_payload, dict) else []
    counterpoint_records = pitch_harmony_payload.get("counterpoint", []) if isinstance(pitch_harmony_payload, dict) else []
    tuning_records = pitch_harmony_payload.get("tuning_system", []) if isinstance(pitch_harmony_payload, dict) else []

    def _pick_slice(records: list[dict[str, Any]], start_seconds: float | None, end_seconds: float | None) -> dict[str, Any]:
        if not records:
            return {}
        if start_seconds is None or end_seconds is None:
            return records[0]
        for record in records:
            if not isinstance(record, dict):
                continue
            rs = record.get("start_seconds")
            re = record.get("end_seconds")
            if rs is None or re is None:
                continue
            try:
                if float(re) >= float(start_seconds) and float(rs) <= float(end_seconds):
                    return record
            except Exception:  # noqa: BLE001
                continue
        return records[0]

    def _attach_pitch_harmony_refs(record: dict[str, Any]) -> None:
        if not pitch_harmony_ref:
            return
        record["pitch_harmony_refs"] = {"pitch_harmony_features_path": pitch_harmony_ref}
        if isinstance(record.get("feature_refs"), dict):
            record["feature_refs"]["pitch_harmony_features_path"] = pitch_harmony_ref

    def _attach_pitch_harmony_stats(record: dict[str, Any]) -> None:
        if not pitch_harmony_ref:
            return
        start = record.get("start_seconds")
        end = record.get("end_seconds")
        obs = _pick_slice([item for item in pitch_observations if isinstance(item, dict)], start, end)
        interval = _pick_slice([item for item in interval_analysis if isinstance(item, dict)], start, end)
        sonority = _pick_slice([item for item in sonority_records if isinstance(item, dict)], start, end)
        movement = _pick_slice([item for item in movement_records if isinstance(item, dict)], start, end)
        counterpoint = _pick_slice([item for item in counterpoint_records if isinstance(item, dict)], start, end)
        tuning = _pick_slice([item for item in tuning_records if isinstance(item, dict)], start, end)
        if "pitch_range" not in record:
            record["pitch_range"] = obs.get("pitch_range")
        if "pitch_class_summary" not in record:
            hist = obs.get("pitch_class_histogram", {}) if isinstance(obs.get("pitch_class_histogram"), dict) else {}
            record["pitch_class_summary"] = hist.get("normalized", {})
        if "interval_class_summary" not in record:
            record["interval_class_summary"] = interval.get("interval_class_histogram", {})
        if "register_summary" not in record:
            record["register_summary"] = obs.get("register_distribution", {})
        record["sonority_type_candidate"] = sonority.get("sonority_type_candidate")
        record["voice_leading_summary"] = movement.get("voice_leading_proxy", {})
        record["counterpoint_summary"] = counterpoint.get("motion_proxy_summary", {})
        record["tuning_summary"] = {
            "microtonal_analysis_available": tuning.get("microtonal_analysis_available"),
            "microtonal_evidence_type": tuning.get("microtonal_evidence_type"),
            "microtonal_confidence": tuning.get("microtonal_confidence"),
        }

    for idx, record in enumerate(ai_records):
        source_record_id = str(record.get("record_id", f"source_{idx:06d}"))
        route = routing_by_source.get(source_record_id, {})
        route_state = str(route.get("content_state", "unknown")) if route else None
        route_conf = float(route.get("route_confidence", route.get("confidence", 0.0)) or 0.0) if route else None
        upgrade_candidates = upgrade_by_source.get(source_record_id, [])
        classification = classify_record_for_export(record, window_rel, quality_payload if isinstance(quality_payload, dict) else {})
        split = str(classification.get("split", "review_required_records"))
        tier = str(classification.get("tier", "low"))
        weight = float(classification.get("weight", 0.0) or 0.0)
        reasons = [str(item) for item in classification.get("reasons", [])] if isinstance(classification.get("reasons"), list) else []

        if split == "quarantined_records":
            export_record = {
                **record,
                "export_record_id": f"{source_record_id}:quarantine:0",
                "source_record_id": source_record_id,
                "export_split": split,
                "trust_tier": tier,
                "training_weight": weight,
                "inclusion_reason": "; ".join(reasons) if reasons else "quarantine conditions met",
                "excluded_fields": [],
            }
            if route_state is not None:
                export_record["content_state"] = route_state
                export_record["route_confidence"] = route_conf
                export_record["routing_refs"] = routing_refs
            _attach_pitch_harmony_refs(export_record)
            export_record["model_source_refs"] = model_source_refs
            export_record["theory_source_refs"] = theory_source_refs
            export_record["external_feature_refs"] = external_feature_refs
            export_record["witness_agreement_summary"] = witness_agreement_summary[:8]
            export_record["witness_conflict_warnings"] = witness_conflict_warnings[:8]
            export_record["review_recommendations"] = witness_review_recommendations[:8]
            if model_consensus_ref:
                export_record["consensus_refs"] = {"model_consensus_ref": model_consensus_ref}
            if upgrade_candidates:
                export_record["label_upgrade_candidate_refs"] = upgrade_candidates
            if upgrade_refs_path:
                export_record["label_upgrade_candidates_path"] = upgrade_refs_path
            split_records[split].append(export_record)
            continue

        accepted_observation, excluded_fields = make_accepted_observation_record(record, window_rel)
        for field_name in excluded_fields:
            excluded_field_summary[field_name] = excluded_field_summary.get(field_name, 0) + 1

        weak_label_record = make_weak_label_record(record)
        review_record = make_review_required_record(record, reasons)
        meter_view = _meter_time_view(
            record,
            micro_rows=meter_micro_rows,
            grid_rows=meter_grid_rows,
            macro_rows=meter_macro_rows,
            meter_hypotheses=meter_hypotheses,
            meter_path=meter_path,
        )

        can_emit_observation = tier in {"high", "medium"} and float(weight) >= 0.6
        if can_emit_observation:
            observation_export = {
                **accepted_observation,
                "export_record_id": f"{source_record_id}:observation:0",
                "source_record_id": source_record_id,
                "export_split": "accepted_records",
                "trust_tier": tier,
                "training_weight": weight,
                "inclusion_reason": "; ".join(reasons) if reasons else "observation fields accepted from reliable source",
                "excluded_fields": excluded_fields,
            }
            if route_state is not None:
                observation_export["content_state"] = route_state
                observation_export["route_confidence"] = route_conf
                observation_export["routing_refs"] = routing_refs
            if meter_view:
                observation_export["local_tempo_bpm"] = meter_view.get("local_tempo_bpm")
                observation_export["grid_confidence"] = meter_view.get("grid_confidence")
                observation_export["subdivision_type"] = meter_view.get("subdivision_type")
                observation_export["pulse_stability"] = meter_view.get("pulse_stability")
                observation_export["meter_time_refs"] = meter_view.get("meter_time_refs")
            _attach_pitch_harmony_refs(observation_export)
            observation_export["model_source_refs"] = model_source_refs
            observation_export["theory_source_refs"] = theory_source_refs
            observation_export["external_feature_refs"] = external_feature_refs
            observation_export["witness_agreement_summary"] = witness_agreement_summary[:8]
            observation_export["witness_conflict_warnings"] = witness_conflict_warnings[:8]
            observation_export["review_recommendations"] = witness_review_recommendations[:8]
            if model_consensus_ref:
                observation_export["consensus_refs"] = {"model_consensus_ref": model_consensus_ref}
            _attach_pitch_harmony_stats(observation_export)
            split_records["accepted_records"].append(observation_export)
        elif split == "audio_midi_only_records":
            observation_export = {
                **accepted_observation,
                "export_record_id": f"{source_record_id}:observation:0",
                "source_record_id": source_record_id,
                "export_split": "audio_midi_only_records",
                "trust_tier": tier,
                "training_weight": weight,
                "inclusion_reason": "; ".join(reasons) if reasons else "audio/midi context only",
                "excluded_fields": excluded_fields,
            }
            if route_state is not None:
                observation_export["content_state"] = route_state
                observation_export["route_confidence"] = route_conf
                observation_export["routing_refs"] = routing_refs
            if meter_view:
                observation_export["local_tempo_bpm"] = meter_view.get("local_tempo_bpm")
                observation_export["grid_confidence"] = meter_view.get("grid_confidence")
                observation_export["subdivision_type"] = meter_view.get("subdivision_type")
                observation_export["pulse_stability"] = meter_view.get("pulse_stability")
                observation_export["meter_time_refs"] = meter_view.get("meter_time_refs")
            _attach_pitch_harmony_refs(observation_export)
            observation_export["model_source_refs"] = model_source_refs
            observation_export["theory_source_refs"] = theory_source_refs
            observation_export["external_feature_refs"] = external_feature_refs
            observation_export["witness_agreement_summary"] = witness_agreement_summary[:8]
            observation_export["witness_conflict_warnings"] = witness_conflict_warnings[:8]
            observation_export["review_recommendations"] = witness_review_recommendations[:8]
            if model_consensus_ref:
                observation_export["consensus_refs"] = {"model_consensus_ref": model_consensus_ref}
            _attach_pitch_harmony_stats(observation_export)
            split_records["audio_midi_only_records"].append(observation_export)

        if str(record.get("label_status", "")) in {"weak_label", "heuristic_estimate", "interpretive_weak_label", "model_prediction"}:
            weak_export = {
                **weak_label_record,
                "export_record_id": f"{source_record_id}:weak_label:0",
                "source_record_id": source_record_id,
                "export_split": "weak_label_records",
                "trust_tier": tier,
                "training_weight": min(weight, 0.7),
                "inclusion_reason": "field-level weak label separated from accepted observations",
                "excluded_fields": [],
            }
            if route_state is not None:
                weak_export["content_state"] = route_state
                weak_export["route_confidence"] = route_conf
                weak_export["routing_refs"] = routing_refs
            if meter_view:
                weak_export["local_tempo_bpm"] = meter_view.get("local_tempo_bpm")
                weak_export["grid_confidence"] = meter_view.get("grid_confidence")
                weak_export["subdivision_type"] = meter_view.get("subdivision_type")
                weak_export["pulse_stability"] = meter_view.get("pulse_stability")
                weak_export["microtiming_summary"] = meter_view.get("microtiming_summary")
                weak_export["macro_section_candidate"] = meter_view.get("macro_section_candidate")
                weak_export["meter_time_ambiguity"] = meter_view.get("meter_time_ambiguity")
                weak_export["meter_hypothesis_candidates"] = meter_view.get("meter_hypothesis_candidates")
                weak_export["meter_time_refs"] = meter_view.get("meter_time_refs")
            _attach_pitch_harmony_refs(weak_export)
            weak_export["model_source_refs"] = model_source_refs
            weak_export["theory_source_refs"] = theory_source_refs
            weak_export["external_feature_refs"] = external_feature_refs
            weak_export["witness_agreement_summary"] = witness_agreement_summary[:8]
            weak_export["witness_conflict_warnings"] = witness_conflict_warnings[:8]
            weak_export["review_recommendations"] = witness_review_recommendations[:8]
            if model_consensus_ref:
                weak_export["consensus_refs"] = {"model_consensus_ref": model_consensus_ref}
            _attach_pitch_harmony_stats(weak_export)
            if upgrade_candidates:
                weak_export["label_upgrade_candidate_refs"] = upgrade_candidates
            if upgrade_refs_path:
                weak_export["label_upgrade_candidates_path"] = upgrade_refs_path
            split_records["weak_label_records"].append(weak_export)

        if split == "review_required_records":
            review_export = {
                **review_record,
                "export_record_id": f"{source_record_id}:review:0",
                "source_record_id": source_record_id,
                "export_split": "review_required_records",
                "trust_tier": tier,
                "training_weight": min(weight, 0.4),
                "inclusion_reason": "; ".join(reasons) if reasons else "review required",
                "excluded_fields": [],
            }
            if route_state is not None:
                review_export["content_state"] = route_state
                review_export["route_confidence"] = route_conf
                review_export["routing_refs"] = routing_refs
            if meter_view:
                review_export["local_tempo_bpm"] = meter_view.get("local_tempo_bpm")
                review_export["grid_confidence"] = meter_view.get("grid_confidence")
                review_export["subdivision_type"] = meter_view.get("subdivision_type")
                review_export["pulse_stability"] = meter_view.get("pulse_stability")
                review_export["microtiming_summary"] = meter_view.get("microtiming_summary")
                review_export["macro_section_candidate"] = meter_view.get("macro_section_candidate")
                review_export["meter_time_ambiguity"] = meter_view.get("meter_time_ambiguity")
                review_export["meter_hypothesis_candidates"] = meter_view.get("meter_hypothesis_candidates")
                review_export["meter_time_refs"] = meter_view.get("meter_time_refs")
            _attach_pitch_harmony_refs(review_export)
            review_export["model_source_refs"] = model_source_refs
            review_export["theory_source_refs"] = theory_source_refs
            review_export["external_feature_refs"] = external_feature_refs
            review_export["witness_agreement_summary"] = witness_agreement_summary[:8]
            review_export["witness_conflict_warnings"] = witness_conflict_warnings[:8]
            review_export["review_recommendations"] = witness_review_recommendations[:8]
            if model_consensus_ref:
                review_export["consensus_refs"] = {"model_consensus_ref": model_consensus_ref}
            _attach_pitch_harmony_stats(review_export)
            if upgrade_candidates:
                review_export["label_upgrade_candidate_refs"] = upgrade_candidates
            if upgrade_refs_path:
                review_export["label_upgrade_candidates_path"] = upgrade_refs_path
            split_records["review_required_records"].append(review_export)

    for split_name, records in split_records.items():
        output_path = export_root / f"{split_name}.jsonl"
        lines = [_line_dump(record) for record in records]
        output_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    manifest = {
        "performance_id": ctx["performance_id"],
        "segment_run_id": ctx["segment_run_id"],
        "source_feature_pack_path": feature_dir.as_posix(),
        "created_at": now_iso(),
        "pipeline_git_commit": _git_commit(),
        "source_ai_record_count": len(ai_records),
        "accepted_observation_count": len(split_records["accepted_records"]),
        "weak_label_count": len(split_records["weak_label_records"]),
        "audio_midi_only_count": len(split_records["audio_midi_only_records"]),
        "review_required_count": len(split_records["review_required_records"]),
        "quarantined_count": len(split_records["quarantined_records"]),
        "field_trust_policy_version": POLICY_VERSION,
        "counts_per_split": {name: len(records) for name, records in split_records.items()},
        "inclusion_rules_used": {
            "accepted": "field-level observation subset derived from reliable source records.",
            "weak_label": "separate weak-label payloads with evidence/confidence metadata.",
            "audio_midi_only": "observation-only exports from reliable records without safe labels.",
            "review_required": "ambiguous/low-confidence/experimental records with review reasons.",
            "quarantined": "critical schema/provenance/time-range failures.",
        },
        "excluded_field_summary": excluded_field_summary,
        "limitations": [
            "Field-level splitting is heuristic and should be periodically recalibrated.",
            "Weak and interpretive labels remain non-ground-truth signals.",
        ],
        "routing_refs": routing_refs,
        "label_upgrade_candidates_path": upgrade_refs_path,
        "pitch_harmony_features_path": pitch_harmony_ref,
        "meter_time_features_path": meter_path,
        "model_sources_used": model_source_refs,
        "theory_sources_used": theory_source_refs,
        "external_feature_refs": external_feature_refs,
        "external_witnesses_available": available_external_witnesses,
        "external_witnesses_missing": missing_external_witnesses,
        "consensus_status": "available" if model_consensus_ref else "missing",
        "model_consensus_ref": model_consensus_ref,
        "witness_agreement_summary": witness_agreement_summary,
        "witness_conflict_warnings": witness_conflict_warnings,
        "review_recommendations": witness_review_recommendations,
    }
    save_json(export_root / "export_manifest.json", manifest)
    return export_root.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Export trusted training dataset splits for one performance.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    args = parser.parse_args()
    output = export_training_dataset_splits(Path(args.performance_manifest))
    print(f"TRAINING_EXPORT_DIR={output.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
