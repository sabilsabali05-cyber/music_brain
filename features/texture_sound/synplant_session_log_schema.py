from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SynplantSessionLog:
    session_id: str
    patch_name: str
    seed_strategy: str
    rating: int
    notes: str
    training_allowed: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "patch_name": self.patch_name,
            "seed_strategy": self.seed_strategy,
            "rating": self.rating,
            "notes": self.notes,
            "training_allowed": self.training_allowed,
        }


def validate_synplant_session_log(payload: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not str(payload.get("session_id", "")).strip():
        errors.append("session_id is required")
    if not str(payload.get("patch_name", "")).strip():
        errors.append("patch_name is required")
    rating = int(payload.get("rating", 0) or 0)
    if rating < 1 or rating > 5:
        errors.append("rating must be between 1 and 5")
    return (len(errors) == 0), errors
