from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AbletonReviewDecision:
    human_review_required: bool
    checklist: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "human_review_required": self.human_review_required,
            "checklist": list(self.checklist),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
        }


DEFAULT_REVIEW_CHECKLIST: list[str] = [
    "Confirm proposed commands match musical intent.",
    "Confirm destructive edits are explicitly approved.",
    "Confirm generated candidates include provenance metadata.",
    "Confirm source-separated/transcribed evidence is treated as witness_not_truth.",
    "Confirm no private paths are present in reports.",
    "Confirm no real Ableton execution is requested.",
]


def evaluate_review_policy(
    *,
    risk_warnings: list[str],
    validation_errors: list[str],
    commands_executed: bool,
) -> AbletonReviewDecision:
    blockers = list(validation_errors)
    if commands_executed:
        blockers.append("Real execution is not allowed in Ableton Agent Bridge scaffold.")
    return AbletonReviewDecision(
        human_review_required=True,
        checklist=list(DEFAULT_REVIEW_CHECKLIST),
        blockers=blockers,
        warnings=list(risk_warnings),
    )
