from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

SUPPORTED_TASK_TYPES = {
    "demucs_source_separation",
    "essentia_embedding",
    "muq_embedding",
    "mert_embedding",
    "yourmt3_transcription_witness",
    "basic_pitch_transcription_witness",
    "text2midi_symbolic_generation",
    "moonbeam_symbolic_generation",
    "midigpt_symbolic_generation",
    "musicbert_ranking",
}


@dataclass(frozen=True)
class CloudJobRequest:
    stage_name: str
    task_type: str
    provider_id: str
    model_id: str
    input_id: str
    execute: bool
    allow_cloud_execution: bool
    allow_upload: bool
    authorization_status: str
    explicitly_authorized_for_execution: bool
    requested_budget_usd: float
    estimated_cost_usd: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CloudJobResult:
    status: str
    reason: str
    task_type: str
    provider_id: str
    model_id: str
    input_id: str
    job_started: bool = False
    upload_performed: bool = False
    download_performed: bool = False
    artifact_path: str | None = None
    provenance_verified: bool = False
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
