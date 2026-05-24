from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class FeedbackTrainingDecision:
    trainable: bool
    reason: str
    witness_semantics: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def can_train_from_feedback(record: dict[str, Any]) -> FeedbackTrainingDecision:
    source_type = str(record.get("source_type", "")).lower()
    auth_status = str(record.get("authorization_status", "")).lower()
    human_reviewed = bool(record.get("human_reviewed", False))
    feedback_type = str(record.get("feedback_type", "")).lower()

    if source_type in {"splice", "production_only", "copyrighted"}:
        return FeedbackTrainingDecision(
            trainable=False,
            reason="splice_or_production_only_source_excluded_from_training",
            witness_semantics="excluded",
        )

    if auth_status in {"", "unknown", "undeclared", "copyrighted", "restricted"}:
        return FeedbackTrainingDecision(
            trainable=False,
            reason="unknown_or_restricted_authorization_excluded_from_training",
            witness_semantics="excluded",
        )

    if source_type in {"separated_stem", "demucs_stem"}:
        return FeedbackTrainingDecision(
            trainable=False,
            reason="separated_stems_are_weak_evidence_not_ground_truth",
            witness_semantics="weak_evidence",
        )

    if source_type in {"transcription_witness", "yourmt3", "basic_pitch"}:
        return FeedbackTrainingDecision(
            trainable=False,
            reason="transcription_is_witness_not_truth",
            witness_semantics="witness_not_truth",
        )

    if feedback_type in {"ranker_feedback", "preference_feedback"}:
        return FeedbackTrainingDecision(
            trainable=True,
            reason="user_feedback_allowed_for_ranker_preference_training",
            witness_semantics="feedback_allowed",
        )

    if source_type == "generated_midi":
        return FeedbackTrainingDecision(
            trainable=human_reviewed,
            reason=(
                "generated_midi_trainable_only_after_human_review"
                if human_reviewed
                else "generated_midi_blocked_until_human_review"
            ),
            witness_semantics="human_review_required",
        )

    return FeedbackTrainingDecision(
        trainable=False,
        reason="fine_tuning_requires_validated_corpus",
        witness_semantics="validated_corpus_required",
    )
