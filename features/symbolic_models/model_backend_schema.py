from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

SymbolicModelCapability = Literal[
    "midi_continuation",
    "midi_infill",
    "text_to_midi",
    "multitrack_generation",
    "controllable_generation",
    "symbolic_embedding",
    "style_classification",
    "similarity_scoring",
    "accompaniment_suggestion",
    "reranking",
    "explanation",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SymbolicModelProvider:
    provider_id: str
    display_name: str
    capabilities: list[SymbolicModelCapability] = field(default_factory=list)
    default_role: str = ""
    role_hint: str = ""
    installation_hint: str = ""


@dataclass
class SymbolicGenerationRequest:
    provider_id: str
    generative_dataset_folder: str
    task_type: str
    prompt: str | None = None
    conditioning: dict[str, Any] = field(default_factory=dict)
    count: int = 4
    mode: str = "direct_target"
    split: str = "train"
    input_examples: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SymbolicGenerationResult:
    provider_id: str
    available: bool
    generation_status: str
    output_midi_paths: list[str] = field(default_factory=list)
    report_path: str | None = None
    summary_path: str | None = None
    limitations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=now_iso)


@dataclass
class SymbolicScoringRequest:
    provider_id: str
    midi_path: str
    reference_midi_path: str | None = None
    task_type: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SymbolicScoringResult:
    provider_id: str
    available: bool
    scoring_status: str
    score: float | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)


@dataclass
class SymbolicEmbeddingResult:
    provider_id: str
    available: bool
    embedding_status: str
    embedding_dimension: int = 0
    embedding_vector: list[float] = field(default_factory=list)
    embedding_reference: str | None = None
    limitations: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)


@dataclass
class ModelAvailabilityReport:
    provider_id: str
    display_name: str
    available: bool
    capabilities: list[SymbolicModelCapability] = field(default_factory=list)
    default_role: str = ""
    role_hint: str = ""
    installation_hint: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)
    checked_at: str = field(default_factory=now_iso)
