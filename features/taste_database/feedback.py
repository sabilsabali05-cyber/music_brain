from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .schema import hash_identifier, redact_private_path

DECISION_LABELS = {"promote", "keep", "adapt", "archive", "reject"}
FOCUS_CATEGORIES = {"groove", "harmony", "melody", "rhythm", "texture", "arrangement", "energy", "mix", "emotion", "novelty"}
SENTIMENT_LABELS = {"positive", "neutral", "negative"}


@dataclass(frozen=True)
class UserFeedbackRecord:
    feedback_id: str
    loop_id: str
    taste_item_id: str
    decision_label: str
    focus_category: str
    sentiment: str
    reviewer_hash: str
    comment_text: str = ""
    source_redacted_path_hint: str = "<PRIVATE_LOCAL_PATH>/unknown"
    witness_ids: list[str] = field(default_factory=list)
    training_allowed: bool = False

    def __post_init__(self) -> None:
        if not self.loop_id.strip():
            raise ValueError("feedback must attach to non-empty loop_id")
        decision = self.decision_label.strip().lower()
        if decision not in DECISION_LABELS:
            raise ValueError("invalid decision_label")
        object.__setattr__(self, "decision_label", decision)
        focus = self.focus_category.strip().lower()
        if focus not in FOCUS_CATEGORIES:
            raise ValueError("invalid focus_category")
        object.__setattr__(self, "focus_category", focus)
        sentiment = self.sentiment.strip().lower()
        if sentiment not in SENTIMENT_LABELS:
            raise ValueError("invalid sentiment")
        object.__setattr__(self, "sentiment", sentiment)
        object.__setattr__(self, "source_redacted_path_hint", redact_private_path(self.source_redacted_path_hint))
        if self.training_allowed:
            raise ValueError("training must remain disabled by default")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def create_feedback_record(
    feedback_id: str,
    loop_id: str,
    taste_item_id: str,
    decision_label: str,
    focus_category: str,
    sentiment: str,
    reviewer: str,
    comment_text: str = "",
    source_path_hint: str = "",
    witness_ids: list[str] | None = None,
) -> UserFeedbackRecord:
    return UserFeedbackRecord(
        feedback_id=feedback_id,
        loop_id=loop_id,
        taste_item_id=taste_item_id,
        decision_label=decision_label,
        focus_category=focus_category,
        sentiment=sentiment,
        reviewer_hash=hash_identifier(reviewer),
        comment_text=comment_text,
        source_redacted_path_hint=source_path_hint,
        witness_ids=list(witness_ids or []),
        training_allowed=False,
    )
