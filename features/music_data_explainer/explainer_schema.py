from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Literal

ExplainerQuestionCategory = Literal[
    "dataset_overview",
    "performance_summary",
    "generative_examples",
    "tangible_generation",
    "ableton_export",
    "sample_library",
    "synplant_seed_selection",
    "readiness_blockers",
    "model_training_readiness",
    "controlled_ingestion_next_steps",
    "privacy_and_authorization",
    "unknown",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class EvidenceReference:
    artifact_path: str
    summary: str
    privacy_redacted: bool = False


@dataclass
class MusicDataLimitation:
    limitation_id: str
    description: str
    severity: Literal["low", "medium", "high"] = "medium"


@dataclass
class MusicDataSourceSummary:
    source_id: str
    artifact_path: str
    exists: bool
    privacy_redacted: bool = False
    notes: list[str] = field(default_factory=list)


@dataclass
class PerformanceSummary:
    performance_id: str
    display_name: str
    generative_dataset_count: int = 0
    generative_example_count: int = 0
    task_types: list[str] = field(default_factory=list)
    evidence_refs: list[EvidenceReference] = field(default_factory=list)


@dataclass
class GenerativeDatasetSummary:
    dataset_id: str
    dataset_path: str
    performance_id: str
    example_count: int
    task_types: list[str] = field(default_factory=list)
    split_counts: dict[str, int] = field(default_factory=dict)
    privacy_redacted: bool = False


@dataclass
class SampleLibrarySummary:
    library_id: str
    manifest_found: bool
    sample_count: int | None = None
    indexed_audio_files: int | None = None
    source_type: str = "unknown"
    privacy_redacted: bool = False
    notes: list[str] = field(default_factory=list)


@dataclass
class AbletonOutputSummary:
    export_available: bool
    export_root: str
    midi_track_count: int = 0
    track_roles: list[str] = field(default_factory=list)
    als_generation_status: str = "not_implemented_experimental_future"
    notes: list[str] = field(default_factory=list)


@dataclass
class ReadinessSummary:
    ready_for_controlled_batch: bool
    ready_for_mass_ingestion: bool
    ready_for_model_training: bool
    blockers: list[str] = field(default_factory=list)
    top_strengths: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    privacy_new_public_leak_count: int = 0
    privacy_historical_debt_count: int = 0


@dataclass
class ExplainerQuestion:
    question_text: str
    category: ExplainerQuestionCategory


@dataclass
class ExplainerAnswer:
    question_text: str
    category: ExplainerQuestionCategory
    answer_markdown: str
    confidence: Literal["high", "medium", "low"] = "medium"
    evidence_refs: list[EvidenceReference] = field(default_factory=list)
    limitations: list[MusicDataLimitation] = field(default_factory=list)


@dataclass
class MusicDataKnowledgePack:
    built_at: str = field(default_factory=now_iso)
    sources: list[MusicDataSourceSummary] = field(default_factory=list)
    performances: list[PerformanceSummary] = field(default_factory=list)
    generative_datasets: list[GenerativeDatasetSummary] = field(default_factory=list)
    sample_libraries: list[SampleLibrarySummary] = field(default_factory=list)
    ableton_output: AbletonOutputSummary = field(
        default_factory=lambda: AbletonOutputSummary(export_available=False, export_root="outputs/ableton_project_v1/AI_Generated_Song_Project")
    )
    readiness: ReadinessSummary = field(
        default_factory=lambda: ReadinessSummary(
            ready_for_controlled_batch=False,
            ready_for_mass_ingestion=False,
            ready_for_model_training=False,
        )
    )
    known_task_types: list[str] = field(default_factory=list)
    corpus_split_counts: dict[str, int] = field(default_factory=dict)
    tangible_outputs: dict[str, str | int | float | bool] = field(default_factory=dict)
    limitations: list[MusicDataLimitation] = field(default_factory=list)
    next_best_actions: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)
