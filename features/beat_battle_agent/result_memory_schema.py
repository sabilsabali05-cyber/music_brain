from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class BeatBattleResultMemory(BaseModel):
    result_id: str
    round_id: str
    placement: int | None = None
    score: float | None = None
    submitted: bool = False
    result_logged: bool = False
    source_authorized_for_learning: bool = True
    authorization_status: str = "authorized"
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
