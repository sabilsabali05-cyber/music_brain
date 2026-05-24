from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class WitnessSource:
    model_id: str
    witness_role: str
    confidence: float
    witness_not_truth: bool = True

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InteractionEvidence:
    source_event_id: str
    target_event_id: str
    interaction_type: str
    confidence: float
    rhythmic_lock: float | None = None
    call_response_score: float | None = None
    spectral_masking_score: float | None = None
    harmony_support_score: float | None = None
    melodic_contour_relation: str | None = None
    density_relation: str | None = None
    notes: list[str] = field(default_factory=list)
    witness_sources: list[WitnessSource] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["witness_sources"] = [item.as_dict() for item in self.witness_sources]
        return payload


@dataclass
class VoiceNode:
    node_id: str
    voice_name: str
    stem_id: str
    onset_events: list[float] = field(default_factory=list)
    note_events: list[str] = field(default_factory=list)
    confidence: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VoiceInteractionGraph:
    status: str
    graph_generated: bool
    graph_id: str
    voices: list[VoiceNode]
    interactions: list[InteractionEvidence]
    witness_not_truth: bool
    witness_sources: list[WitnessSource] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "graph_generated": self.graph_generated,
            "graph_id": self.graph_id,
            "voices": [row.as_dict() for row in self.voices],
            "interactions": [row.as_dict() for row in self.interactions],
            "witness_not_truth": self.witness_not_truth,
            "witness_sources": [row.as_dict() for row in self.witness_sources],
        }
