from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Literal

ReadinessCategory = Literal[
    "source authorization",
    "dedupe/hash coverage",
    "metadata coverage",
    "transcription success rate",
    "segmentation success rate",
    "merged MIDI coverage",
    "rhythm feature coverage",
    "meter/time feature coverage",
    "pitch/harmony feature coverage",
    "routing/content-state coverage",
    "external witness coverage",
    "model consensus coverage",
    "generative example yield",
    "review burden",
    "storage budget",
    "human review queue readiness",
    "local sample-library readiness",
    "Synplant seed-selection readiness",
    "Pure Data template readiness",
    "Max/Ableton routing readiness",
    "ratio intelligence readiness",
    "symbolic backend readiness",
    "training tokenization readiness",
    "model evaluation readiness",
    "model-training readiness",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class IngestionRiskFlag:
    risk_id: str
    category: ReadinessCategory
    severity: Literal["low", "medium", "high", "critical"]
    blocked: bool
    summary: str
    mitigation: str = ""


@dataclass
class DatasetScaleEstimate:
    performances_indexed: int = 0
    generative_examples_count: int = 0
    sample_library_index_available: bool = False
    storage_budget_note: str = "unknown"


@dataclass
class ReviewBurdenEstimate:
    review_required_examples: int = 0
    estimated_hours: float = 0.0
    human_review_queue_ready: bool = False
    burden_level: Literal["low", "medium", "high"] = "high"


@dataclass
class FeatureLayerReadiness:
    transcription_success_rate_known: bool = False
    segmentation_success_rate_known: bool = False
    merged_midi_coverage_known: bool = False
    rhythm_feature_coverage_known: bool = False
    meter_time_feature_coverage_known: bool = False
    pitch_harmony_feature_coverage_known: bool = False
    routing_content_state_coverage_known: bool = False
    external_witness_coverage_known: bool = False
    model_consensus_coverage_known: bool = False


@dataclass
class SoundLibraryReadiness:
    sample_library_indexer_available: bool = False
    sample_library_records_present_locally: bool = False
    synplant_session_logging_ready: bool = False
    pure_data_template_library_ready: bool = False
    max_ableton_routing_records_ready: bool = False
    sound_feedback_capture_ready: bool = False


@dataclass
class ModelTrainingReadiness:
    training_tokenization_target_ready: bool = False
    export_target_ready: bool = False
    ratio_intelligence_schema_ready: bool = False
    model_training_has_happened: bool = False
    synplant_automation_available: bool = False
    pure_data_automation_available: bool = False


@dataclass
class TrainingReadinessGate:
    category: ReadinessCategory
    status: Literal["ready", "partial", "blocked", "unknown"]
    blocked: bool
    details: str


@dataclass
class ControlledBatchPlan:
    ready_for_controlled_batch: bool
    recommended_next_batch_size: int
    suggested_scope: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class MassIngestionReadinessReport:
    created_at: str
    ready_for_mass_ingestion: bool
    ready_for_controlled_batch: bool
    ready_for_model_training: bool
    recommended_next_batch_size: int
    top_strengths: list[str] = field(default_factory=list)
    top_blockers: list[str] = field(default_factory=list)
    required_next_actions: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    risk_flags: list[IngestionRiskFlag] = field(default_factory=list)
    gates: list[TrainingReadinessGate] = field(default_factory=list)
    dataset_scale_estimate: DatasetScaleEstimate = field(default_factory=DatasetScaleEstimate)
    review_burden_estimate: ReviewBurdenEstimate = field(default_factory=ReviewBurdenEstimate)
    feature_layer_readiness: FeatureLayerReadiness = field(default_factory=FeatureLayerReadiness)
    sound_library_readiness: SoundLibraryReadiness = field(default_factory=SoundLibraryReadiness)
    model_training_readiness: ModelTrainingReadiness = field(default_factory=ModelTrainingReadiness)
    controlled_batch_plan: ControlledBatchPlan = field(
        default_factory=lambda: ControlledBatchPlan(
            ready_for_controlled_batch=True,
            recommended_next_batch_size=10,
        )
    )
    limitations: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def build_current_state_readiness_report() -> MassIngestionReadinessReport:
    return MassIngestionReadinessReport(
        created_at=now_iso(),
        ready_for_mass_ingestion=False,
        ready_for_controlled_batch=True,
        ready_for_model_training=False,
        recommended_next_batch_size=10,
        top_strengths=[],
        top_blockers=[],
        required_next_actions=[],
        strengths=[],
        blockers=[],
    )
