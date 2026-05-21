from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ProviderRequested = Literal["fake", "mt3", "yourmt3"]
ProviderUsed = Literal["fake", "mt3", "yourmt3", "none"]
Backend = Literal["local_fake", "modal_fake", "modal"]
Status = Literal["success", "failed"]


class LatencySeconds(BaseModel):
    checksum: float = 0.0
    copy_input: float = 0.0
    ffmpeg_convert: float = 0.0
    transcription: float = 0.0
    total: float = 0.0


class ArtifactPaths(BaseModel):
    input_audio: str
    normalized_audio: str
    full_mix_midi: str
    job_report: str


class ErrorDetails(BaseModel):
    stage: str
    message: str
    exception_type: str


class JobReport(BaseModel):
    track_id: str
    input_filename: str
    checksum: str = ""
    duration_seconds: float = 0.0
    provider_requested: ProviderRequested
    provider_used: ProviderUsed = "none"
    fallback_used: bool = False
    fallback_reason: str | None = None
    model_version: str = ""
    backend: Backend
    status: Status
    latency_seconds: LatencySeconds = Field(default_factory=LatencySeconds)
    artifacts: ArtifactPaths
    error: ErrorDetails | None = None


class PreflightCheck(BaseModel):
    name: str
    ok: bool
    message: str


class PreflightReport(BaseModel):
    ok: bool
    checks: list[PreflightCheck]
    python_version: str
    cwd: str
    provider: str
    backend: str
    library_root: str
