from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from features.model_witnesses import redact_private_path


def _redact_private_values(value: Any) -> Any:
    if isinstance(value, str):
        return redact_private_path(value)
    if isinstance(value, list):
        return [_redact_private_values(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _redact_private_values(item) for key, item in value.items()}
    return value


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
        object.__setattr__(self, "source_audio_ref", redact_private_path(self.source_audio_ref))
        object.__setattr__(self, "policy_separation", _redact_private_values(self.policy_separation))
        object.__setattr__(self, "provenance", _redact_private_values(self.provenance))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
