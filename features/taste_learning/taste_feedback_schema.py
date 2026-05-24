from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


CORE_TASTE_LABELS = {"love", "like", "neutral", "dislike", "reject"}


def clamp01(value: float | int | None) -> float:
    if value is None:
        return 0.0
    out = float(value)
    if out < 0.0:
        return 0.0
    if out > 1.0:
        return 1.0
    return out


@dataclass(frozen=True)
class TasteFeedbackRecord:
    feedback_id: str
    generation_id: str
    candidate_id: str
    authorization_status: str
    source_authorized_for_learning: bool
    reviewer: str
    taste_label: str
    accepted: bool
    musicality_score: float
    groove_score: float
    harmony_score: float
    notes: str = ""
    tags: list[str] = field(default_factory=list)
    blocked_by_policy: bool = False

    def __post_init__(self) -> None:
        label = self.taste_label.strip().lower()
        object.__setattr__(self, "taste_label", label)
        object.__setattr__(self, "musicality_score", clamp01(self.musicality_score))
        object.__setattr__(self, "groove_score", clamp01(self.groove_score))
        object.__setattr__(self, "harmony_score", clamp01(self.harmony_score))
        blocked = self.blocked_by_policy
        if self.authorization_status.strip().lower() not in {"authorized", "public_domain", "self_owned"}:
            blocked = True
        if not self.source_authorized_for_learning:
            blocked = True
        object.__setattr__(self, "blocked_by_policy", blocked)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_taste_feedback(payload: dict[str, Any]) -> tuple[bool, str]:
    label = str(payload.get("taste_label", "")).strip().lower()
    if label not in CORE_TASTE_LABELS:
        return False, "invalid_taste_label"
    auth = str(payload.get("authorization_status", "")).strip().lower()
    if auth not in {"authorized", "public_domain", "self_owned"}:
        return False, "unauthorized_feedback_source"
    if not bool(payload.get("source_authorized_for_learning", False)):
        return False, "source_not_authorized_for_learning"
    return True, "ok"
