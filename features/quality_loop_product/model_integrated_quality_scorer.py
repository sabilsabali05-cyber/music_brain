from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class EnsembleScoringSummary:
    callable_witness_models: list[str]
    required_missing_models: list[str]
    quality_multiplier: float
    score_offset: float
    blockers: list[str]
    fallbacks: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def build_ensemble_scoring_summary(baseline_payload: dict[str, Any]) -> EnsembleScoringSummary:
    models = baseline_payload.get("models", [])
    rows = [row for row in models if isinstance(row, dict)]
    callable_models = [str(row.get("model", "")) for row in rows if bool(row.get("callable_witness", False))]
    required_missing = [
        str(row.get("model", ""))
        for row in rows
        if bool(row.get("witness_required", False)) and not bool(row.get("callable_witness", False))
    ]
    fallbacks = [f"{row.get('model')}:{row.get('fallback_behavior')}" for row in rows if not bool(row.get("callable_witness", False))]
    optional_callable_count = len([name for name in callable_models if name not in {"basicpitch", "demucs"}])

    base_multiplier = 1.0
    if "basicpitch" in callable_models:
        base_multiplier += 0.06
    if "demucs" in callable_models:
        base_multiplier += 0.06
    base_multiplier += min(0.12, optional_callable_count * 0.03)
    if required_missing:
        base_multiplier -= 0.15
    quality_multiplier = round(_clamp(base_multiplier, 0.65, 1.2), 6)

    score_offset = 0.0
    if "basicpitch" not in callable_models:
        score_offset -= 0.2
    if "demucs" not in callable_models:
        score_offset -= 0.1

    blockers = [f"required_witness_missing:{name}" for name in required_missing]
    return EnsembleScoringSummary(
        callable_witness_models=callable_models,
        required_missing_models=required_missing,
        quality_multiplier=quality_multiplier,
        score_offset=round(score_offset, 6),
        blockers=blockers,
        fallbacks=fallbacks,
    )

