from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class RetrievalMemoryPolicy:
    retrieval_first: bool = True
    generation_enabled: bool = False
    reroll_enabled: bool = False
    pattern_box_enabled: bool = False
    training_allowed: bool = False
    training_gate_conditions: list[str] = field(
        default_factory=lambda: [
            "explicit_product_approval",
            "privacy_scan_zero_new_leaks",
            "authorization_audit_passed",
            "local_only_training_plan",
            "rollback_plan_verified",
        ]
    )

    def __post_init__(self) -> None:
        if not self.retrieval_first:
            raise ValueError("retrieval_first must remain enabled")
        if self.generation_enabled or self.reroll_enabled or self.pattern_box_enabled:
            raise ValueError("generation/reroll/pattern-box are disabled")
        if self.training_allowed:
            raise ValueError("training must be disabled by default")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def rank_by_feedback_memory(candidates: list[dict[str, Any]], feedback_index: dict[str, float]) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []
    for row in candidates:
        loop_id = str(row.get("loop_id", ""))
        memory_score = float(feedback_index.get(loop_id, 0.0))
        out = dict(row)
        out["retrieval_memory_score"] = round(memory_score, 6)
        scored.append(out)
    scored.sort(key=lambda item: float(item.get("retrieval_memory_score", 0.0)), reverse=True)
    return scored
