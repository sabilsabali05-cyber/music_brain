from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ModelIntegrationRecord:
    model_id: str
    family: str
    role_in_music_brain: str
    input_modalities: list[str]
    output_modalities: list[str]
    expected_tasks: list[str]
    local_config_required: bool
    weights_required: bool
    training_allowed: bool
    fine_tune_possible: bool
    user_personalization_path: str
    safety_policy: str
    availability_status: str
    unavailable_reason: str
    smoke_test_supported: bool
    limitations: list[str]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
