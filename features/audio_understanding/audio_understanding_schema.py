from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class AudioUnderstandingModelRecord:
    model_id: str
    role: str
    enabled_by_default: bool
    smoke_test_supported: bool
    expected_outputs: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
