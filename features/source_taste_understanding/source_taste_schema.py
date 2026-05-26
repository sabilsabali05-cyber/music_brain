from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class SourceDatabaseGenerativePrinciple:
    principle_id: str
    statement: str
    rationale: str
    supporting_witnesses: list[str]
    confidence: float
    evidence_quality: str
    transformation_not_copy_note: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SourceTasteDossier:
    dossier_id: str
    generated_at: str
    source_items_considered: int
    source_items_analyzed: int
    strongest_principles: list[dict[str, Any]]
    weak_evidence_limits: list[str]
    witness_influence_summary: list[str]
    rejected_principles: list[str]
    transformation_vs_copy_policy: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
