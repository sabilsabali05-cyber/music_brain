from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class SourceSeparationWitnessStatus:
    status: str
    demucs_configured: bool
    demucs_available: bool
    smoke_test_passed: bool
    source_separation_performed: bool
    stems_generated: bool
    downloads_performed: bool
    model_training_has_occurred: bool
    witness_policy: str
    training_use_allowed: str = "false_by_default"
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
