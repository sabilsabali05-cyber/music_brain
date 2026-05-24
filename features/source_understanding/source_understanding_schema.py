from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def clamp01(value: float | int | None) -> float:
    if value is None:
        return 0.0
    out = float(value)
    if out < 0.0:
        return 0.0
    if out > 1.0:
        return 1.0
    return out


def redact_private_path(value: str) -> str:
    return (
        str(value)
        .replace("C:/Users/", "<PRIVATE_LOCAL_PATH>/")
        .replace("C:\\Users\\", "<PRIVATE_LOCAL_PATH>\\")
        .replace("/Users/", "<PRIVATE_LOCAL_PATH>/")
    )


@dataclass(frozen=True)
class SourceUnderstandingRecord:
    record_id: str
    item_id: str
    source_artifact: str
    source_path_redacted: str
    source_type: str
    authorization_status: str
    training_allowed: bool
    retrieval_allowed: bool
    raw_audio_processing_allowed: bool
    evidence_types: list[str]
    evidence_summary: str
    confidence: float
    confidence_band: str
    confidence_reason: str
    usable_as_generation_evidence: bool
    blocked_by_policy: bool
    blocked_by_confidence: bool
    policy_block_reasons: list[str] = field(default_factory=list)
    generation_tags: list[str] = field(default_factory=list)
    generation_controls: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", clamp01(self.confidence))
        object.__setattr__(self, "source_path_redacted", redact_private_path(self.source_path_redacted))
        if self.confidence >= 0.8:
            band = "high"
        elif self.confidence >= 0.5:
            band = "medium"
        else:
            band = "low"
        object.__setattr__(self, "confidence_band", band)
        if self.blocked_by_policy:
            object.__setattr__(self, "usable_as_generation_evidence", False)
        if self.blocked_by_confidence:
            object.__setattr__(self, "usable_as_generation_evidence", False)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_source_understanding_record(
    *,
    record_id: str,
    item_id: str,
    source_artifact: str,
    source_path_redacted: str,
    source_type: str,
    authorization_status: str,
    training_allowed: bool,
    retrieval_allowed: bool,
    raw_audio_processing_allowed: bool,
    evidence_types: list[str],
    evidence_summary: str,
    confidence: float,
    confidence_reason: str,
    policy_block_reasons: list[str] | None = None,
    generation_tags: list[str] | None = None,
    generation_controls: dict[str, Any] | None = None,
) -> SourceUnderstandingRecord:
    auth = authorization_status.strip().lower() or "unknown"
    policy_blocks = list(policy_block_reasons or [])
    blocked_policy = auth in {"unauthorized", "restricted", "private", "unknown"} or (not retrieval_allowed)
    if not raw_audio_processing_allowed and source_type in {"raw_audio", "source_audio"}:
        policy_blocks.append("raw_audio_processing_not_authorized_locally")
        blocked_policy = True
    if blocked_policy and "authorization_or_policy_gate" not in policy_blocks:
        policy_blocks.append("authorization_or_policy_gate")
    blocked_confidence = clamp01(confidence) < 0.5
    usable = not blocked_policy and not blocked_confidence
    return SourceUnderstandingRecord(
        record_id=record_id,
        item_id=item_id,
        source_artifact=source_artifact,
        source_path_redacted=source_path_redacted,
        source_type=source_type,
        authorization_status=auth,
        training_allowed=bool(training_allowed),
        retrieval_allowed=bool(retrieval_allowed),
        raw_audio_processing_allowed=bool(raw_audio_processing_allowed),
        evidence_types=sorted({str(x) for x in evidence_types if str(x).strip()}),
        evidence_summary=evidence_summary,
        confidence=clamp01(confidence),
        confidence_band="low",
        confidence_reason=confidence_reason,
        usable_as_generation_evidence=usable,
        blocked_by_policy=blocked_policy,
        blocked_by_confidence=blocked_confidence,
        policy_block_reasons=policy_blocks,
        generation_tags=list(generation_tags or []),
        generation_controls=dict(generation_controls or {}),
    )
