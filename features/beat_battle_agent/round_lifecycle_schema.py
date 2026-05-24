from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class RoundLifecycleStatus(str, Enum):
    discovered = "discovered"
    sounds_acquired = "sounds_acquired"
    variations_generated = "variations_generated"
    drafts_generated = "drafts_generated"
    drafts_ranked = "drafts_ranked"
    submission_blocked = "submission_blocked"
    submission_attempted = "submission_attempted"
    submitted = "submitted"
    result_logged = "result_logged"
    blocked = "blocked"


class BeatBattleRoundLifecycle(BaseModel):
    round_id: str
    status: RoundLifecycleStatus
    watcher_detected_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    sounds_acquired_at: str = ""
    variations_generated_at: str = ""
    drafts_generated_at: str = ""
    ranked_at: str = ""
    submission_attempted_at: str = ""
    submitted_at: str = ""
    result_logged_at: str = ""
    blocker: str = ""
    notes: list[str] = Field(default_factory=list)
