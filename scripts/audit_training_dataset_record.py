from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.feature_dataset_common import load_json, now_iso, save_json
from scripts.trust_common import load_jsonl_records, resolve_performance_context, trust_dir
from features.model_sources import MODEL_SOURCES
from features.theory_sources import THEORY_SOURCES


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = load_json(path)
    return payload if isinstance(payload, dict) else {}


def _label_counts(ai_records: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in ai_records:
        status = str(record.get("label_status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
    return counts


def audit_training_dataset_record(performance_manifest_path: Path) -> tuple[Path, Path]:
    ctx = resolve_performance_context(performance_manifest_path)
    feature_dir = ctx["feature_dir"]
    trust_output_dir = trust_dir(feature_dir)

    rhythm_path = feature_dir / "rhythm_features.json"
    harmony_path = feature_dir / "harmony_features.json"
    tags_path = feature_dir / "tags.json"
    meter_time_path = feature_dir / "rhythm_time" / "meter_time_features.json"
    pitch_harmony_path = feature_dir / "pitch_harmony" / "pitch_harmony_features.json"
    ai_path = feature_dir / "ai_training_records.jsonl"
    manifest_path = feature_dir / "feature_pack_manifest.json"
    merge_report_path = ctx["segments_manifest_path"].parent / "merged" / "merge_report.json"
    reliability_path = trust_output_dir / "transcription_reliability.json"
    quality_path = trust_output_dir / "quality_gates.json"
    routing_dir = feature_dir / "routing"
    external_dir = feature_dir / "external_model_features"

    rhythm_payload = _read_json_if_exists(rhythm_path)
    harmony_payload = _read_json_if_exists(harmony_path)
    tags_payload = _read_json_if_exists(tags_path)
    meter_time_payload = _read_json_if_exists(meter_time_path)
    pitch_harmony_payload = _read_json_if_exists(pitch_harmony_path)
    ai_records = load_jsonl_records(ai_path)
    reliability_payload = _read_json_if_exists(reliability_path)
    quality_payload = _read_json_if_exists(quality_path)
    routing_asset_payload = _read_json_if_exists(routing_dir / "asset_classification.json")
    routing_regions_payload = _read_json_if_exists(routing_dir / "content_region_routes.json")
    routing_decisions_payload = _read_json_if_exists(routing_dir / "analysis_routing_decisions.json")
    routing_diagnostics_payload = _read_json_if_exists(routing_dir / "routing_diagnostics.json")
    upgrade_candidates_payload = _read_json_if_exists(trust_output_dir / "label_upgrade_candidates.json")
    model_consensus_payload = _read_json_if_exists(external_dir / "model_consensus.json")

    quality_status = str(quality_payload.get("overall_quality_status", "review_required"))
    inclusion_decision = quality_status
    recommended_split = str(quality_payload.get("recommended_dataset_split", "review"))

    strong_usable = [
        "MIDI note events and transcription window timing",
        "Merged MIDI artifact (if present) and stitch diagnostics",
        "Raw rhythm density and velocity statistics",
        "Pitch-class histograms and transcription statuses",
    ]
    weak_usable = [
        "Chord label candidates",
        "Rhythm/chord region candidates",
        "Motif and rhythm-family candidates",
        "Ontology/semantic interpretation tags",
    ]
    experimental = [
        "Rhythm-family classifications without strong calibration support",
        "Philosophical rhythm concept labels",
        "Syncopation and groove proxy inferences",
        "Motif ranking/importance heuristics",
    ]

    missing_data: list[str] = []
    if not (external_dir / "essentia_features.json").exists():
        missing_data.append("Essentia descriptors")
    if not (external_dir / "musicnn_features.json").exists():
        missing_data.append("musicnn semantic tags")
    if not (external_dir / "feature_consensus.json").exists():
        missing_data.append("external model consensus")
    if not any(str(record.get("verification_status", "unverified")) == "human_verified" for record in ai_records):
        missing_data.append("human verification labels")
    if not (external_dir / "beat_tracker_features.json").exists():
        missing_data.append("beat/downbeat external witness")

    reliability_summary = reliability_payload.get("summary", {}) if isinstance(reliability_payload.get("summary"), dict) else {}
    label_status_counts = _label_counts(ai_records)
    region_counts = routing_regions_payload.get("content_state_counts", {}) if isinstance(routing_regions_payload.get("content_state_counts"), dict) else {}
    routing_decisions = routing_decisions_payload.get("decisions", []) if isinstance(routing_decisions_payload.get("decisions"), list) else []
    suppressed_labels = sum(
        len(item.get("suppressed_labels", []))
        for item in routing_decisions
        if isinstance(item, dict) and isinstance(item.get("suppressed_labels"), list)
    )
    upgrade_candidates = upgrade_candidates_payload.get("candidates", []) if isinstance(upgrade_candidates_payload.get("candidates"), list) else []
    upgrade_summary = upgrade_candidates_payload.get("summary", {}) if isinstance(upgrade_candidates_payload.get("summary"), dict) else {}
    content_state_counts_by_granularity = routing_diagnostics_payload.get("content_state_counts_by_granularity", {})
    likely_false_suppressions = routing_diagnostics_payload.get("potential_false_suppressions", [])
    harmonic_evidence_suppressed = routing_diagnostics_payload.get("harmonic_evidence_not_classified_harmonic", [])

    upgrade_by_family: dict[str, int] = {}
    downgrade_or_suppress_by_family: dict[str, int] = {}
    for candidate in upgrade_candidates:
        if not isinstance(candidate, dict):
            continue
        family = str(candidate.get("label_family", "unknown"))
        status = str(candidate.get("recommended_label_status", ""))
        if status == "upgrade_candidate":
            upgrade_by_family[family] = upgrade_by_family.get(family, 0) + 1
        elif status in {"downgrade_candidate", "suppress_candidate"}:
            downgrade_or_suppress_by_family[family] = downgrade_or_suppress_by_family.get(family, 0) + 1

    calibration_status = "monitor"
    if len(likely_false_suppressions) == 0 and len(harmonic_evidence_suppressed) <= 3:
        calibration_status = "healthy"
    elif len(likely_false_suppressions) >= 20 or len(harmonic_evidence_suppressed) >= 50:
        calibration_status = "needs_recalibration"

    routing_readiness = {
        "asset_type": routing_asset_payload.get("asset_type", "unknown"),
        "asset_confidence": routing_asset_payload.get("confidence", 0.0),
        "content_state_counts": region_counts,
        "content_state_counts_by_granularity": content_state_counts_by_granularity,
        "labels_suppressed_by_routing": suppressed_labels,
        "likely_false_suppressions": len(likely_false_suppressions) if isinstance(likely_false_suppressions, list) else 0,
        "harmonic_evidence_regions_suppressed": len(harmonic_evidence_suppressed) if isinstance(harmonic_evidence_suppressed, list) else 0,
        "upgrade_candidates": int(upgrade_summary.get("upgrade_candidate", 0) or 0),
        "upgrade_candidates_by_label_family": upgrade_by_family,
        "downgrade_or_suppress_candidates": int(upgrade_summary.get("downgrade_candidate", 0) or 0)
        + int(upgrade_summary.get("suppress_candidate", 0) or 0),
        "downgrade_or_suppress_candidates_by_label_family": downgrade_or_suppress_by_family,
        "needs_human_review_candidates": int(upgrade_summary.get("needs_human_review", 0) or 0),
        "routing_improves_training_safety": bool(region_counts) or bool(upgrade_candidates),
        "recommended_routing_calibration_status": calibration_status,
    }
    field_level_usability = {
        "observation_only_exports_expected": True,
        "safe_fields_for_training": [
            "timing boundaries (start/end/duration)",
            "note count and note density",
            "velocity statistics",
            "pitch-class histograms",
            "transcription reliability score and recommended weight",
            "feature/provenance references",
        ],
        "weak_label_fields": [
            "chord label candidates",
            "rhythm-family candidates",
            "motif group references",
            "interpretive ontology tags",
        ],
        "review_required_fields": [
            "ambiguous rhythm-family outputs",
            "low-confidence harmony/rhythm labels",
            "interpretive philosophical tags",
            "conflicting model-derived interpretations",
        ],
        "can_train_on_raw_timing_midi_now": True,
        "semantic_rhythm_harmony_labels_status": "weak_or_review_only",
    }
    pitch_harmony_summary = {
        "safe_observations": [
            "pitch range and register distribution",
            "pitch-class normalized summary",
            "interval-class histogram summary",
            "voicing span and note-density/polyphony proxies",
            "direct-derived voice-count estimate proxies",
        ],
        "weak_labels": [
            "chord/key/mode hypotheses",
            "cadence/modulation candidates",
            "sonority family candidates",
            "counterpoint interpretation labels",
            "microtonal system hypotheses",
            "tension-release or experimental harmony labels",
        ],
        "external_audio_tuning_limitations": [
            "symbolic MIDI pitch classes do not directly prove tuning system",
            "audio-based intonation estimation is required for non-12TET certainty",
        ],
        "microtonal_limitations": [
            "lack of pitch-bend/non-12TET evidence should remain inconclusive",
            "absence of evidence is not evidence of strict 12TET",
        ],
        "experimental_harmony_limitations": [
            "nonfunctional/cluster-color labels remain candidate-level",
            "avoid using interpretive harmony labels as hard ground truth",
        ],
        "training_usefulness": "safe_stats_high_utility_weak_labels_review_required",
        "microtonal_analysis_available": pitch_harmony_payload.get("microtonal_analysis_available"),
        "microtonal_evidence_type": pitch_harmony_payload.get("microtonal_evidence_type"),
        "microtonal_confidence": pitch_harmony_payload.get("microtonal_confidence"),
    }
    meter_summary = meter_time_payload.get("summary", {}) if isinstance(meter_time_payload.get("summary"), dict) else {}
    meter_hypotheses = meter_time_payload.get("beat_meter_hypotheses", []) if isinstance(meter_time_payload.get("beat_meter_hypotheses"), list) else []
    top_meter = meter_hypotheses[0] if meter_hypotheses and isinstance(meter_hypotheses[0], dict) else {}
    meter_confidence = float(meter_time_payload.get("confidence", 0.0) or 0.0)
    meter_ambiguity = float(meter_time_payload.get("ambiguity", 1.0) or 1.0)
    meter_usefulness = "weak_or_review_only"
    if meter_confidence >= 0.65 and meter_ambiguity <= 0.45:
        meter_usefulness = "safe_for_observation_fields"
    meter_safe_fields = ["local_tempo_bpm", "grid_confidence", "subdivision_type", "pulse_stability", "meter_time_refs"]
    meter_weak_fields = ["microtiming_summary", "macro_section_candidate", "meter_hypothesis_candidates", "meter_time_ambiguity"]

    external_refs = {
        "essentia_features": (external_dir / "essentia_features.json").resolve().as_posix() if (external_dir / "essentia_features.json").exists() else None,
        "musicnn_features": (external_dir / "musicnn_features.json").resolve().as_posix() if (external_dir / "musicnn_features.json").exists() else None,
        "beat_tracker_features": (external_dir / "beat_tracker_features.json").resolve().as_posix() if (external_dir / "beat_tracker_features.json").exists() else None,
        "music21_features": (external_dir / "music21_features.json").resolve().as_posix() if (external_dir / "music21_features.json").exists() else None,
        "omnizart_availability": (external_dir / "omnizart_availability.json").resolve().as_posix() if (external_dir / "omnizart_availability.json").exists() else None,
        "model_consensus_ref": (external_dir / "model_consensus.json").resolve().as_posix() if (external_dir / "model_consensus.json").exists() else None,
    }
    available_witnesses = sorted([name for name, value in external_refs.items() if value and name != "model_consensus_ref"])
    unavailable_witnesses = sorted([name for name, value in external_refs.items() if not value and name != "model_consensus_ref"])
    source_coverage = {
        "theory_sources_represented": sorted({str(item.get("source_id")) for item in THEORY_SOURCES}),
        "model_sources_represented": sorted({str(item.get("provider_id")) for item in MODEL_SOURCES}),
        "available_external_witnesses": available_witnesses,
        "unavailable_external_witnesses": unavailable_witnesses,
        "consensus_status": "available" if external_refs["model_consensus_ref"] else "missing",
        "what_became_more_trusted": model_consensus_payload.get("confidence_boosts", []),
        "what_remains_weak_or_review_only": model_consensus_payload.get("unresolved_conflicts", []),
        "witness_agreement_summary": model_consensus_payload.get("agreements", []),
        "witness_conflict_warnings": model_consensus_payload.get("disagreements", []),
        "review_recommendations": model_consensus_payload.get("recommended_review_items", []),
    }

    audit_json = {
        "performance_id": ctx["performance_id"],
        "segment_run_id": ctx["segment_run_id"],
        "created_at": now_iso(),
        "artifacts": {
            "source_audio_reference": str(ctx["performance_manifest"].get("source_path")),
            "active_analysis_path": str(ctx["analysis_path"]) if ctx["analysis_path"] else None,
            "active_segments_manifest": ctx["segments_manifest_path"].as_posix(),
            "window_midi_count": int(reliability_summary.get("window_count", 0) or 0),
            "merged_midi_path": str(ctx["merged_midi_path"]) if ctx["merged_midi_path"] else None,
            "merge_report_path": merge_report_path.resolve().as_posix() if merge_report_path.exists() else None,
            "feature_pack_files": {
                "rhythm_features": rhythm_path.resolve().as_posix() if rhythm_path.exists() else None,
                "harmony_features": harmony_path.resolve().as_posix() if harmony_path.exists() else None,
                "tags": tags_path.resolve().as_posix() if tags_path.exists() else None,
                "meter_time_features": meter_time_path.resolve().as_posix() if meter_time_path.exists() else None,
                "feature_pack_manifest": manifest_path.resolve().as_posix() if manifest_path.exists() else None,
            },
            "ai_jsonl_path": ai_path.resolve().as_posix() if ai_path.exists() else None,
        },
        "strongly_usable_data": strong_usable,
        "usable_as_weak_labels": weak_usable,
        "experimental_low_confidence_data": experimental,
        "missing_data": missing_data,
        "ai_readiness_assessment": {
            "ai_jsonl_usable": ai_path.exists() and len(ai_records) > 0,
            "safe_for_training_now": [
                "raw_observation and derived_observation records",
                "high/medium reliability windows",
                "records with complete provenance fields",
            ],
            "weak_labels_only": [
                "heuristic_estimate records",
                "weak_label and interpretive_weak_label records",
            ],
            "exclude_or_downweight": [
                "failed/missing reliability windows",
                "review_required records",
                "ambiguous labels without corroboration",
            ],
            "label_status_counts": label_status_counts,
            "reliability_summary": reliability_summary,
        },
        "field_level_training_usability": field_level_usability,
        "meter_time_intelligence": {
            "confidence": meter_confidence,
            "ambiguity": meter_ambiguity,
            "top_meter_hypothesis": top_meter,
            "subdivision_histogram": meter_summary.get("subdivision_histogram", {}),
            "macro_section_candidates": meter_summary.get("macro_section_candidates", []),
            "usefulness": meter_usefulness,
            "safe_observation_fields": meter_safe_fields,
            "weak_or_review_fields": meter_weak_fields,
        },
        "pitch_harmony_tuning_intelligence": pitch_harmony_summary,
        "theory_and_model_source_coverage": source_coverage,
        "routing_and_label_upgrade_readiness": routing_readiness,
        "dataset_inclusion_decision": inclusion_decision,
        "recommended_dataset_split": recommended_split,
        "recommended_next_steps": [
            "Collect human verification for high-impact weak labels.",
            "Use accepted/audio_midi_only splits for baseline training first.",
            "Review quarantined/review records before inclusion.",
        ],
    }

    audit_json_path = trust_output_dir / "training_data_audit.json"
    save_json(audit_json_path, audit_json)

    report_dir = Path("reports") / "data_audits"
    report_dir.mkdir(parents=True, exist_ok=True)
    audit_md_path = report_dir / f"{ctx['performance_id']}_training_data_audit.md"
    lines = [
        f"# Training Data Audit - {ctx['performance_id']}",
        "",
        "## 1. Artifacts generated",
        f"- source audio reference: `{audit_json['artifacts']['source_audio_reference']}`",
        f"- active analysis path: `{audit_json['artifacts']['active_analysis_path']}`",
        f"- active segments manifest: `{audit_json['artifacts']['active_segments_manifest']}`",
        f"- window MIDI count: `{audit_json['artifacts']['window_midi_count']}`",
        f"- merged MIDI path: `{audit_json['artifacts']['merged_midi_path']}`",
        f"- merge report path: `{audit_json['artifacts']['merge_report_path']}`",
        f"- feature pack files: `{json.dumps(audit_json['artifacts']['feature_pack_files'], ensure_ascii=True)}`",
        f"- AI JSONL path: `{audit_json['artifacts']['ai_jsonl_path']}`",
        "",
        "## 2. Strongly usable data",
    ]
    lines.extend(f"- {item}" for item in strong_usable)
    lines.extend(["", "## 3. Usable as weak labels"])
    lines.extend(f"- {item}" for item in weak_usable)
    lines.extend(["", "## 4. Experimental / low-confidence data"])
    lines.extend(f"- {item}" for item in experimental)
    lines.extend(["", "## 5. Missing data"])
    if missing_data:
        lines.extend(f"- {item}" for item in missing_data)
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## 6. AI-readiness assessment",
            f"- Is ai_training_records.jsonl usable? `{audit_json['ai_readiness_assessment']['ai_jsonl_usable']}`",
            f"- Safe for training now: `{json.dumps(audit_json['ai_readiness_assessment']['safe_for_training_now'], ensure_ascii=True)}`",
            f"- Weak labels only: `{json.dumps(audit_json['ai_readiness_assessment']['weak_labels_only'], ensure_ascii=True)}`",
            f"- Exclude/downweight: `{json.dumps(audit_json['ai_readiness_assessment']['exclude_or_downweight'], ensure_ascii=True)}`",
            "",
            "## 7. Dataset inclusion decision",
            f"- decision: `{inclusion_decision}`",
            f"- recommended split: `{recommended_split}`",
            "",
            "## Field-Level Training Usability",
            "- accepted_records may intentionally be observation-only to avoid weak-label contamination.",
            f"- safe fields: `{json.dumps(field_level_usability['safe_fields_for_training'], ensure_ascii=True)}`",
            f"- weak-label fields: `{json.dumps(field_level_usability['weak_label_fields'], ensure_ascii=True)}`",
            f"- review-required fields: `{json.dumps(field_level_usability['review_required_fields'], ensure_ascii=True)}`",
            f"- train on raw timing/MIDI now: `{field_level_usability['can_train_on_raw_timing_midi_now']}`",
            f"- semantic/rhythm/harmony labels status: `{field_level_usability['semantic_rhythm_harmony_labels_status']}`",
            "",
            "## Meter and Time Intelligence",
            f"- confidence: `{meter_confidence}`",
            f"- ambiguity: `{meter_ambiguity}`",
            f"- top meter hypothesis: `{json.dumps(top_meter, ensure_ascii=True)}`",
            f"- subdivision histogram: `{json.dumps(meter_summary.get('subdivision_histogram', {}), ensure_ascii=True)}`",
            f"- macro section candidates: `{json.dumps(meter_summary.get('macro_section_candidates', []), ensure_ascii=True)}`",
            f"- usefulness: `{meter_usefulness}`",
            f"- safe observation fields: `{json.dumps(meter_safe_fields, ensure_ascii=True)}`",
            f"- weak/review fields: `{json.dumps(meter_weak_fields, ensure_ascii=True)}`",
            "",
            "## 8. Recommended next steps",
        ]
    )
    lines.extend(f"- {item}" for item in audit_json["recommended_next_steps"])
    lines.extend(
        [
            "",
            "## Pitch, Harmony, and Tuning Intelligence",
            f"- safe observations: `{json.dumps(pitch_harmony_summary['safe_observations'], ensure_ascii=True)}`",
            f"- weak labels: `{json.dumps(pitch_harmony_summary['weak_labels'], ensure_ascii=True)}`",
            f"- external audio/tuning limitations: `{json.dumps(pitch_harmony_summary['external_audio_tuning_limitations'], ensure_ascii=True)}`",
            f"- microtonal limitations: `{json.dumps(pitch_harmony_summary['microtonal_limitations'], ensure_ascii=True)}`",
            f"- experimental harmony limitations: `{json.dumps(pitch_harmony_summary['experimental_harmony_limitations'], ensure_ascii=True)}`",
            f"- training usefulness: `{pitch_harmony_summary['training_usefulness']}`",
            f"- microtonal analysis available: `{pitch_harmony_summary['microtonal_analysis_available']}`",
            f"- microtonal evidence type: `{pitch_harmony_summary['microtonal_evidence_type']}`",
            f"- microtonal confidence: `{pitch_harmony_summary['microtonal_confidence']}`",
            "",
            "## Routing and Label Upgrade Readiness",
            f"- asset_type: `{routing_readiness['asset_type']}`",
            f"- content_state_counts: `{json.dumps(routing_readiness['content_state_counts'], ensure_ascii=True)}`",
            f"- content_state_counts_by_granularity: `{json.dumps(routing_readiness['content_state_counts_by_granularity'], ensure_ascii=True)}`",
            f"- labels_suppressed_by_routing: `{routing_readiness['labels_suppressed_by_routing']}`",
            f"- likely_false_suppressions: `{routing_readiness['likely_false_suppressions']}`",
            f"- harmonic_evidence_regions_suppressed: `{routing_readiness['harmonic_evidence_regions_suppressed']}`",
            f"- upgrade_candidates: `{routing_readiness['upgrade_candidates']}`",
            f"- upgrade_candidates_by_label_family: `{json.dumps(routing_readiness['upgrade_candidates_by_label_family'], ensure_ascii=True)}`",
            f"- downgrade_or_suppress_candidates: `{routing_readiness['downgrade_or_suppress_candidates']}`",
            f"- downgrade_or_suppress_candidates_by_label_family: `{json.dumps(routing_readiness['downgrade_or_suppress_candidates_by_label_family'], ensure_ascii=True)}`",
            f"- needs_human_review_candidates: `{routing_readiness['needs_human_review_candidates']}`",
            f"- routing_improves_training_safety: `{routing_readiness['routing_improves_training_safety']}`",
            f"- recommended_routing_calibration_status: `{routing_readiness['recommended_routing_calibration_status']}`",
            "",
            "## Theory and Model Source Coverage",
            f"- theory_sources_represented: `{json.dumps(source_coverage['theory_sources_represented'], ensure_ascii=True)}`",
            f"- model_sources_represented: `{json.dumps(source_coverage['model_sources_represented'], ensure_ascii=True)}`",
            f"- available_external_witnesses: `{json.dumps(source_coverage['available_external_witnesses'], ensure_ascii=True)}`",
            f"- unavailable_external_witnesses: `{json.dumps(source_coverage['unavailable_external_witnesses'], ensure_ascii=True)}`",
            f"- consensus_status: `{source_coverage['consensus_status']}`",
            f"- what_became_more_trusted: `{json.dumps(source_coverage['what_became_more_trusted'], ensure_ascii=True)}`",
            f"- what_remains_weak_or_review_only: `{json.dumps(source_coverage['what_remains_weak_or_review_only'], ensure_ascii=True)}`",
            f"- witness_agreement_summary: `{json.dumps(source_coverage['witness_agreement_summary'], ensure_ascii=True)}`",
            f"- witness_conflict_warnings: `{json.dumps(source_coverage['witness_conflict_warnings'], ensure_ascii=True)}`",
            f"- review_recommendations: `{json.dumps(source_coverage['review_recommendations'], ensure_ascii=True)}`",
        ]
    )
    audit_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return audit_md_path.resolve(), audit_json_path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit one performance for training-data trust/readiness.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    args = parser.parse_args()
    md_path, json_path = audit_training_dataset_record(Path(args.performance_manifest))
    print(f"TRAINING_AUDIT_MD_PATH={md_path.as_posix()}")
    print(f"TRAINING_AUDIT_JSON_PATH={json_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
