from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class FusionSource:
    source_id: str
    source_type: str
    witness_semantics: str
    enabled: bool
    available: bool
    contribution: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceFusionPlan:
    status: str
    fusion_performed: bool
    graph_generated: bool
    model_training_has_occurred: bool
    summary: list[str]
    sources: list[FusionSource] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "fusion_performed": self.fusion_performed,
            "graph_generated": self.graph_generated,
            "model_training_has_occurred": self.model_training_has_occurred,
            "summary": list(self.summary),
            "sources": [row.as_dict() for row in self.sources],
        }
