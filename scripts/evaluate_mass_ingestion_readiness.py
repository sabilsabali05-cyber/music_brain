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

    sample_records_local = (ROOT_DIR / "datasets" / "sample_libraries" / "local_sounds_desktop" / "sample_seed_records.jsonl").exists()
    sample_indexer_available = (ROOT_DIR / "scripts" / "index_sample_library.py").exists()
    synplant_schema_ready = (ROOT_DIR / "features" / "texture_sound" / "synplant_candidate_schema.py").exists()
    pure_data_schema_ready = (ROOT_DIR / "features" / "generative_systems" / "puredata_schema.py").exists()
    max_routing_schema_ready = (ROOT_DIR / "features" / "texture_sound" / "composition_sound_plan_schema.py").exists()
    ratio_schema_ready = (ROOT_DIR / "features" / "ratio_intelligence" / "ratio_schema.py").exists()
    symbolic_backend_ready = (ROOT_DIR / "features" / "symbolic_models" / "backends" / "registry.py").exists()
    model_eval_tools_ready = (ROOT_DIR / "scripts" / "validate_tangible_demo.py").exists() and (
        ROOT_DIR / "scripts" / "validate_ableton_project_export.py"
    ).exists()

    strengths = [
        "composition pipeline exists",
        "trust/audit layer exists",
        "generative examples exist",
        "prototype MIDI generation exists",
        "symbolic backend sockets exist",
        "local sample-library indexer exists",
        "Ableton project export workflow exists",
    ]

    blockers = [
        "high review burden",
        "missing manual review queue",
        "missing serious model-training tokenization/export target",
        "missing Synplant session logging",
        "missing Pure Data template library",
        "missing Max/Ableton routing records",
        "missing sound feedback capture",
        "incomplete external witness coverage",
        "incomplete meter/pitch/harmony calibration on some performances",
    ]
    required_next_actions = [
        "Run a controlled 5-10 item ingestion batch with authorization-gated manifests.",
        "Implement symbolic tokenization export and validation for training corpus v1.",
        "Add review-pack -> feedback import loop for quality weighting.",
        "Add manual Synplant session logging + rating capture.",
        "Add model-evaluation scorecards for generation iterations.",
    ]

    risk_flags = [
        IngestionRiskFlag(
            risk_id="review_burden_high",
            category="review burden",
            severity="high",
            blocked=True,
            summary="Review backlog is high for safe mass ingestion.",
            mitigation="Run controlled batch of 10 and reduce review queue before scaling.",
        ),
        IngestionRiskFlag(
            risk_id="sound_system_logging_missing",
            category="Synplant seed-selection readiness",
            severity="high",
            blocked=True,
            summary="Synplant/Pure Data/Max routing logs are not production-ready.",
            mitigation="Add manual session logging and routing record capture.",
        ),
    ]

    gates = [
        TrainingReadinessGate("source authorization", "partial", False, "Sample library config supports local authorization claims."),
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
        TrainingReadinessGate("review burden", "blocked", True, "Review burden is currently too high for mass ingestion."),
        TrainingReadinessGate("storage budget", "unknown", False, "No formal storage budget report detected."),
        TrainingReadinessGate("human review queue readiness", "blocked", True, "Manual queue workflow is not codified."),
        TrainingReadinessGate("local sample-library readiness", "partial", False, "Local sample indexing exists with privacy-safe outputs."),
        TrainingReadinessGate("Synplant seed-selection readiness", "blocked", True, "Session logging schemas are placeholders only."),
        TrainingReadinessGate("Pure Data template readiness", "blocked", True, "Template library is not yet established."),
        TrainingReadinessGate("Max/Ableton routing readiness", "blocked", True, "Routing records are placeholder level only."),
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
            "partial" if model_eval_tools_ready else "blocked",
            not model_eval_tools_ready,
            "Basic validators exist; structured model-evaluation scorecards are still missing.",
        ),
        TrainingReadinessGate("model-training readiness", "blocked", True, "Tokenization/export target and feedback loops are missing."),
    ]

    return MassIngestionReadinessReport(
        created_at=now_iso(),
        ready_for_mass_ingestion=False,
        ready_for_controlled_batch=True,
        ready_for_model_training=False,
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
            human_review_queue_ready=False,
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
            synplant_session_logging_ready=synplant_schema_ready,
            pure_data_template_library_ready=pure_data_schema_ready,
            max_ableton_routing_records_ready=max_routing_schema_ready,
            sound_feedback_capture_ready=False,
        ),
        model_training_readiness=ModelTrainingReadiness(
            training_tokenization_target_ready=False,
            export_target_ready=False,
            ratio_intelligence_schema_ready=ratio_schema_ready,
            model_training_has_happened=False,
            synplant_automation_available=False,
            pure_data_automation_available=False,
        ),
        controlled_batch_plan=ControlledBatchPlan(
            ready_for_controlled_batch=True,
            recommended_next_batch_size=10,
            suggested_scope=[
                "5 song/performance files",
                "50 to 100 local sample-library sounds",
                "5 to 10 manually logged Synplant seed attempts later",
                "3 to 5 Pure Data template/control experiments later",
            ],
            notes=[
                "Controlled batch is allowed.",
                "Mass ingestion is blocked until controlled-batch metrics improve.",
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
