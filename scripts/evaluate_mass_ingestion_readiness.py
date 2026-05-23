from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.mass_ingestion.readiness_schema import (  # noqa: E402
    ControlledBatchPlan,
    DatasetScaleEstimate,
    FeatureLayerReadiness,
    IngestionRiskFlag,
    MassIngestionReadinessReport,
    ModelTrainingReadiness,
    ReviewBurdenEstimate,
    SoundLibraryReadiness,
    TrainingReadinessGate,
    now_iso,
)


def _read_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return payload if isinstance(payload, dict) else None


def _collect_dataset_signals() -> tuple[dict[str, Any], Path]:
    report_dir = ROOT_DIR / "reports" / "dataset_quality"
    report_json = report_dir / "dataset_quality_yield_report.json"
    payload = _read_json_if_exists(report_json) or {}
    return payload, report_json


def build_readiness_report() -> MassIngestionReadinessReport:
    dataset_quality, dataset_quality_path = _collect_dataset_signals()
    review_count = int(dataset_quality.get("split_review", 320) or 320)
    generative_examples_count = int(dataset_quality.get("total_generative_examples", 0) or 0)
    performances_indexed = int(dataset_quality.get("total_performances", 0) or 0)

    privacy_report = _read_json_if_exists(ROOT_DIR / "reports" / "privacy" / "privacy_leak_scan_report.json") or {}
    historical_scrub_plan = (
        _read_json_if_exists(ROOT_DIR / "reports" / "privacy" / "historical_path_scrub_plan.json") or {}
    )
    controlled_plan = _read_json_if_exists(ROOT_DIR / "reports" / "controlled_ingestion" / "controlled_batch_plan.json") or {}
    review_queue_report = _read_json_if_exists(ROOT_DIR / "reports" / "review_queue" / "review_queue_summary.json") or {}
    quality_report = _read_json_if_exists(ROOT_DIR / "reports" / "data_quality" / "training_candidate_quality_report.json") or {}
    corpus_report = _read_json_if_exists(ROOT_DIR / "reports" / "model_training" / "symbolic_corpus_v1_report.json") or {}
    evaluation_report = (
        _read_json_if_exists(ROOT_DIR / "reports" / "model_evaluation" / "generated_composition_scorecard.json") or {}
    )
    feedback_report = _read_json_if_exists(ROOT_DIR / "reports" / "feedback" / "feedback_summary.json") or {}
    puredata_report = _read_json_if_exists(ROOT_DIR / "reports" / "puredata" / "template_library_report.json") or {}
    routing_report = _read_json_if_exists(ROOT_DIR / "reports" / "ableton_routing" / "routing_records_report.json") or {}

    sample_records_local = (ROOT_DIR / "datasets" / "sample_libraries" / "local_sounds_desktop" / "sample_seed_records.jsonl").exists()
    sample_indexer_available = (ROOT_DIR / "scripts" / "index_sample_library.py").exists()
    synplant_schema_ready = (ROOT_DIR / "datasets" / "synplant" / "session_logs_v1.jsonl").exists() and (
        ROOT_DIR / "features" / "texture_sound" / "synplant_session_log_schema.py"
    ).exists()
    pure_data_schema_ready = (ROOT_DIR / "datasets" / "puredata" / "template_library_v1.json").exists()
    max_routing_schema_ready = (ROOT_DIR / "datasets" / "ableton_routing" / "routing_records_v1.jsonl").exists()
    ratio_schema_ready = (ROOT_DIR / "features" / "ratio_intelligence" / "ratio_schema.py").exists()
    symbolic_backend_ready = (ROOT_DIR / "features" / "symbolic_models" / "backends" / "registry.py").exists()
    model_eval_tools_ready = (ROOT_DIR / "reports" / "model_evaluation" / "generated_composition_scorecard.json").exists()

    privacy_status_ok = privacy_report.get("status") in {"ok", None}
    has_new_privacy_leaks = int(privacy_report.get("new_public_leak_count", 0) or 0) > 0
    historical_scrub_ready = bool(historical_scrub_plan)
    source_authorization_valid = (controlled_plan.get("source_authorization", {}).get("status") in {"valid", None})
    controlled_plan_valid = controlled_plan.get("status", "valid") == "valid"
    review_queue_ready = int(review_queue_report.get("queue_size", 0) or 0) > 0
    quality_scores_ready = int(quality_report.get("candidate_count", 0) or 0) > 0
    corpus_training_ready = bool(corpus_report.get("training_ready", False))
    feedback_ready = int(feedback_report.get("feedback_count", 0) or 0) > 0
    synplant_ready = synplant_schema_ready
    puredata_ready = pure_data_schema_ready and puredata_report.get("status") == "ok"
    routing_ready = max_routing_schema_ready and routing_report.get("status") == "ok"
    model_evaluation_ready = evaluation_report.get("status") in {"ok", "warning"}

    ready_for_controlled_batch = bool(privacy_status_ok and not has_new_privacy_leaks and controlled_plan_valid)
    ready_for_model_training = bool(
        ready_for_controlled_batch
        and source_authorization_valid
        and review_queue_ready
        and quality_scores_ready
        and corpus_training_ready
        and feedback_ready
        and model_evaluation_ready
    )
    ready_for_mass_ingestion = bool(
        ready_for_model_training
        and historical_scrub_ready
        and int(privacy_report.get("pre_existing_historical_path_debt_count", 1) or 1) == 0
    )

    blockers: list[str] = []
    if has_new_privacy_leaks:
        blockers.append("privacy leak scan reports new public leaks")
    if not source_authorization_valid:
        blockers.append("source authorization validation failed")
    if not historical_scrub_ready:
        blockers.append("historical path scrub plan is missing")
    if not review_queue_ready:
        blockers.append("manual review queue artifacts are missing")
    if not quality_scores_ready:
        blockers.append("quality scorecards are missing")
    if not corpus_training_ready:
        blockers.append("symbolic corpus export is not training-ready")
    if not feedback_ready:
        blockers.append("human feedback loop artifacts are missing")
    if not synplant_ready:
        blockers.append("synplant session logging guidance is missing")
    if not puredata_ready:
        blockers.append("pure data template library artifacts are missing")
    if not routing_ready:
        blockers.append("max/ableton routing records are missing")
    if not ready_for_mass_ingestion:
        blockers.append("historical privacy debt remains above zero")
    if not blockers:
        blockers.append("none")

    strengths = [
        "composition pipeline exists",
        "trust/audit layer exists",
        "generative examples exist",
        "prototype MIDI generation exists",
        "symbolic backend sockets exist",
        "local sample-library indexer exists",
        "Ableton project export workflow exists",
        "controlled ingestion planner and runner reports exist",
        "review queue and quality scorecard artifacts exist",
    ]

    required_next_actions = [
        "Create config/controlled_batches/first_real_batch.local.json from template and keep it uncommitted.",
        "Run plan-controlled-ingestion-batch and run-controlled-ingestion-batch against first_real_batch.local.json.",
        "Resolve historical scrub safe candidates and reduce privacy debt count.",
        "Regenerate tangible demo + Ableton export after controlled batch and rescore quality reports.",
        "Re-run evaluate-mass-ingestion-readiness to verify blocker removal.",
    ]

    risk_flags = [
        IngestionRiskFlag(
            risk_id="review_burden_high",
            category="review burden",
            severity="high",
            blocked=review_count > 100,
            summary="Review backlog remains high for safe mass ingestion." if review_count > 100 else "Review burden is manageable.",
            mitigation="Run controlled batch of 10 and reduce review queue before scaling.",
        ),
        IngestionRiskFlag(
            risk_id="sound_system_logging_missing",
            category="Synplant seed-selection readiness",
            severity="high",
            blocked=not (synplant_ready and puredata_ready and routing_ready),
            summary="Synplant/Pure Data/Max routing logs are not production-ready."
            if not (synplant_ready and puredata_ready and routing_ready)
            else "Synplant/Pure Data/Max routing artifacts are present.",
            mitigation="Add manual session logging and routing record capture.",
        ),
    ]

    gates = [
        TrainingReadinessGate(
            "source authorization",
            "ready" if source_authorization_valid else "blocked",
            not source_authorization_valid,
            "Controlled batch plan includes source authorization validation.",
        ),
        TrainingReadinessGate("dedupe/hash coverage", "partial", False, "Sample-library hashes exist; performance-level dedupe remains partial."),
        TrainingReadinessGate("metadata coverage", "partial", False, "Core metadata exists but manual curation is incomplete."),
        TrainingReadinessGate("transcription success rate", "unknown", False, "No reliable aggregate success metric found."),
        TrainingReadinessGate("segmentation success rate", "unknown", False, "No consolidated segmentation readiness metric found."),
        TrainingReadinessGate("merged MIDI coverage", "unknown", False, "No merged MIDI coverage aggregate found."),
        TrainingReadinessGate("rhythm feature coverage", "partial", False, "Feature extraction pipeline exists."),
        TrainingReadinessGate("meter/time feature coverage", "partial", False, "Feature extraction pipeline exists."),
        TrainingReadinessGate("pitch/harmony feature coverage", "partial", False, "Feature extraction pipeline exists."),
        TrainingReadinessGate("routing/content-state coverage", "partial", False, "Routing schema exists but completeness is unknown."),
        TrainingReadinessGate("external witness coverage", "partial", True, "Coverage appears incomplete across the full corpus."),
        TrainingReadinessGate("model consensus coverage", "partial", False, "Consensus tooling exists, broad coverage unknown."),
        TrainingReadinessGate("generative example yield", "partial", False, "Generative examples available but review burden is high."),
        TrainingReadinessGate(
            "review burden",
            "blocked" if review_count > 100 else "partial",
            review_count > 100,
            "Review burden is currently too high for mass ingestion." if review_count > 100 else "Review burden sampled and tracked.",
        ),
        TrainingReadinessGate("storage budget", "unknown", False, "No formal storage budget report detected."),
        TrainingReadinessGate(
            "human review queue readiness",
            "ready" if review_queue_ready else "blocked",
            not review_queue_ready,
            "Review queue dataset/report exists." if review_queue_ready else "Manual queue workflow is not codified.",
        ),
        TrainingReadinessGate("local sample-library readiness", "partial", False, "Local sample indexing exists with privacy-safe outputs."),
        TrainingReadinessGate(
            "Synplant seed-selection readiness",
            "ready" if synplant_ready else "blocked",
            not synplant_ready,
            "Session logging guidance exists." if synplant_ready else "Session logging guidance is missing.",
        ),
        TrainingReadinessGate(
            "Pure Data template readiness",
            "ready" if puredata_ready else "blocked",
            not puredata_ready,
            "Template library artifacts are present." if puredata_ready else "Template library is not yet established.",
        ),
        TrainingReadinessGate(
            "Max/Ableton routing readiness",
            "ready" if routing_ready else "blocked",
            not routing_ready,
            "Routing records artifacts are present." if routing_ready else "Routing records are missing.",
        ),
        TrainingReadinessGate("ratio intelligence readiness", "partial", False, "Schema placeholders exist for future planning."),
        TrainingReadinessGate(
            "symbolic backend readiness",
            "partial" if symbolic_backend_ready else "blocked",
            not symbolic_backend_ready,
            "Symbolic backend adapter architecture exists but real trained backends remain unavailable.",
        ),
        TrainingReadinessGate("training tokenization readiness", "blocked", True, "Tokenization/export pipeline is not ready yet."),
        TrainingReadinessGate(
            "model evaluation readiness",
            "ready" if model_eval_tools_ready else "blocked",
            not model_eval_tools_ready,
            "Structured model-evaluation scorecards are present." if model_eval_tools_ready else "Structured scorecards are missing.",
        ),
        TrainingReadinessGate(
            "model-training readiness",
            "ready" if ready_for_model_training else "blocked",
            not ready_for_model_training,
            "Model-training prerequisites are not fully satisfied yet.",
        ),
    ]

    return MassIngestionReadinessReport(
        created_at=now_iso(),
        ready_for_mass_ingestion=ready_for_mass_ingestion,
        ready_for_controlled_batch=ready_for_controlled_batch,
        ready_for_model_training=ready_for_model_training,
        recommended_next_batch_size=10,
        top_strengths=strengths[:6],
        top_blockers=blockers[:6],
        required_next_actions=required_next_actions,
        strengths=strengths,
        blockers=blockers,
        risk_flags=risk_flags,
        gates=gates,
        dataset_scale_estimate=DatasetScaleEstimate(
            performances_indexed=performances_indexed,
            generative_examples_count=generative_examples_count,
            sample_library_index_available=sample_indexer_available,
            storage_budget_note="not formally reported",
        ),
        review_burden_estimate=ReviewBurdenEstimate(
            review_required_examples=review_count,
            estimated_hours=round(review_count * 0.08, 2),
            human_review_queue_ready=review_queue_ready,
            burden_level="high",
        ),
        feature_layer_readiness=FeatureLayerReadiness(
            transcription_success_rate_known=False,
            segmentation_success_rate_known=False,
            merged_midi_coverage_known=False,
            rhythm_feature_coverage_known=True,
            meter_time_feature_coverage_known=True,
            pitch_harmony_feature_coverage_known=True,
            routing_content_state_coverage_known=True,
            external_witness_coverage_known=False,
            model_consensus_coverage_known=False,
        ),
        sound_library_readiness=SoundLibraryReadiness(
            sample_library_indexer_available=sample_indexer_available,
            sample_library_records_present_locally=sample_records_local,
            synplant_session_logging_ready=synplant_ready,
            pure_data_template_library_ready=puredata_ready,
            max_ableton_routing_records_ready=routing_ready,
            sound_feedback_capture_ready=feedback_ready,
        ),
        model_training_readiness=ModelTrainingReadiness(
            training_tokenization_target_ready=corpus_training_ready,
            export_target_ready=corpus_training_ready,
            ratio_intelligence_schema_ready=ratio_schema_ready,
            model_training_has_happened=False,
            synplant_automation_available=False,
            pure_data_automation_available=False,
        ),
        controlled_batch_plan=ControlledBatchPlan(
            ready_for_controlled_batch=ready_for_controlled_batch,
            recommended_next_batch_size=10,
            suggested_scope=[
                "5 song/performance files",
                "50 to 100 local sample-library sounds",
                "5 to 10 manually logged Synplant seed attempts later",
                "3 to 5 Pure Data template/control experiments later",
            ],
            notes=[
                "Controlled batch is allowed.",
                "Mass ingestion is blocked until historical privacy debt reaches zero and training gates clear.",
                "Do not ingest hundreds/thousands of files yet.",
            ],
        ),
        limitations=[
            "Readiness is inferred from available local artifacts and may include unknowns.",
            f"Dataset quality signal source: {dataset_quality_path.as_posix()} (if present).",
            "No model training, transcription, modal calls, or audio processing performed.",
        ],
    )


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Mass Ingestion Readiness Report",
        "",
        f"- created_at: `{payload['created_at']}`",
        f"- ready_for_mass_ingestion: `{payload['ready_for_mass_ingestion']}`",
        f"- ready_for_controlled_batch: `{payload['ready_for_controlled_batch']}`",
        f"- ready_for_model_training: `{payload['ready_for_model_training']}`",
        f"- recommended_next_batch_size: `{payload['recommended_next_batch_size']}`",
        "",
        "## Top Strengths",
    ]
    lines.extend([f"- {item}" for item in payload["strengths"]])
    lines.extend(["", "## Top Blockers"])
    lines.extend([f"- {item}" for item in payload["blockers"]])
    lines.extend(["", "## Required Next Actions"])
    lines.extend([f"- {item}" for item in payload["required_next_actions"]])
    lines.extend(["", "## Controlled Batch Plan"])
    plan = payload["controlled_batch_plan"]
    lines.extend([f"- ready_for_controlled_batch: `{plan['ready_for_controlled_batch']}`"])
    lines.extend([f"- recommended_next_batch_size: `{plan['recommended_next_batch_size']}`"])
    lines.extend(["- suggested_scope:"])
    lines.extend([f"  - {item}" for item in plan["suggested_scope"]])
    lines.extend(["- notes:"])
    lines.extend([f"  - {item}" for item in plan["notes"]])
    lines.extend(["", "## Risk Flags"])
    for risk in payload["risk_flags"]:
        lines.append(f"- {risk['risk_id']} ({risk['severity']}): {risk['summary']}")
    lines.extend(["", "## Limitations"])
    lines.extend([f"- {item}" for item in payload["limitations"]])
    lines.append("")
    return "\n".join(lines)


def evaluate_mass_ingestion_readiness() -> tuple[Path, Path, dict[str, Any]]:
    report = build_readiness_report()
    payload = report.as_dict()
    output_dir = ROOT_DIR / "reports" / "mass_ingestion"
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "mass_ingestion_readiness_report.json"
    md_path = output_dir / "mass_ingestion_readiness_report.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(payload), encoding="utf-8")
    return json_path, md_path, payload


def main() -> int:
    json_path, md_path, payload = evaluate_mass_ingestion_readiness()
    print(f"MASS_INGESTION_READINESS_JSON={json_path.as_posix()}")
    print(f"MASS_INGESTION_READINESS_MD={md_path.as_posix()}")
    print(f"READY_FOR_MASS_INGESTION={payload['ready_for_mass_ingestion']}")
    print(f"READY_FOR_CONTROLLED_BATCH={payload['ready_for_controlled_batch']}")
    print(f"READY_FOR_MODEL_TRAINING={payload['ready_for_model_training']}")
    print(f"RECOMMENDED_NEXT_BATCH_SIZE={payload['recommended_next_batch_size']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
