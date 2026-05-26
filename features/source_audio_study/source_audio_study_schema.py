from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from features.model_witnesses import redact_private_path


@dataclass(frozen=True)
class SourceAudioStudyItem:
    item_id: str
    source_audio_ref: str
    source_audio_ref_redacted: str
    authorization_status: str
    retrieval_allowed: bool
    training_allowed: bool
    analysis_allowed: bool
    policy_separation: dict[str, Any]
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_audio_ref_redacted", redact_private_path(self.source_audio_ref_redacted))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
