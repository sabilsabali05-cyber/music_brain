from __future__ import annotations

from dataclasses import dataclass

from .music_intelligence_schema import (
    AUTHORIZATION_ALLOWED_FOR_TRAINING,
    AUTHORIZATION_EXCLUDED,
    AUTHORIZATION_RETRIEVAL_ONLY,
    MusicIntelligenceRecord,
    PromotionDecision,
)


@dataclass(frozen=True)
class PromotionThresholds:
    min_transcription_confidence: float = 0.60
    max_junk_penalty_for_training: float = 0.25
    min_music_value_for_training: float = 0.55
    min_retrieval_value_for_retrieval_only: float = 0.35
    min_training_value_for_training: float = 0.60


def _auth_status(record: MusicIntelligenceRecord) -> str:
    return record.policy_outcome.authorization_status.strip().lower()


def decide_promotion_label(
    record: MusicIntelligenceRecord,
    scores: dict[str, float],
    *,
    thresholds: PromotionThresholds = PromotionThresholds(),
) -> PromotionDecision:
    blockers: list[str] = []
    auth_status = _auth_status(record)

    if auth_status in AUTHORIZATION_EXCLUDED:
        return PromotionDecision(
            promotion_label="excluded",
            reason="authorization_excluded",
            blockers=["authorization_excluded"],
            confidence=1.0,
        )
    if record.policy_outcome.policy_excluded:
        return PromotionDecision(
            promotion_label="excluded",
            reason="policy_excluded",
            blockers=["policy_excluded"],
            confidence=1.0,
        )
    if not record.provenance.source_artifact or not record.provenance.source_path_redacted:
        return PromotionDecision(
            promotion_label="excluded",
            reason="missing_provenance",
            blockers=["missing_provenance"],
            confidence=1.0,
        )

    # Training-safe requires all policy/training gates.
    if auth_status not in AUTHORIZATION_ALLOWED_FOR_TRAINING:
        blockers.append("authorization_not_training_safe")
    if not record.policy_outcome.training_allowed:
        blockers.append("training_not_allowed")
    if not record.policy_outcome.policy_fields_complete:
        blockers.append("policy_fields_incomplete")
    if not record.policy_outcome.labels_complete:
        blockers.append("labels_incomplete")
    if (scores.get("transcription_reliability_score", 0.0) < thresholds.min_transcription_confidence):
        blockers.append("low_transcription_confidence")
    if scores.get("junk_penalty", 1.0) > thresholds.max_junk_penalty_for_training:
        blockers.append("high_junk_penalty")
    if scores.get("overall_music_value_score", 0.0) < thresholds.min_music_value_for_training:
        blockers.append("low_music_value")
    if scores.get("training_value_score", 0.0) < thresholds.min_training_value_for_training:
        blockers.append("low_training_value")

    if not blockers:
        return PromotionDecision(
            promotion_label="training_safe",
            reason="all_training_gates_passed",
            blockers=[],
            confidence=0.95,
        )

    retrieval_value = scores.get("retrieval_value_score", 0.0)
    music_value = scores.get("overall_music_value_score", 0.0)
    has_useful_descriptors = (
        record.harmony_tonality.has_complete_harmony_fields
        or record.rhythm.has_complete_rhythm_fields
        or record.texture_instrumentation.has_complete_texture_fields
        or len(record.valuable_moments) > 0
    )
    retrieval_auth = auth_status in AUTHORIZATION_RETRIEVAL_ONLY.union(AUTHORIZATION_ALLOWED_FOR_TRAINING)
    low_transcription = scores.get("transcription_reliability_score", 0.0) < thresholds.min_transcription_confidence

    retrieval_only_conditions = [
        retrieval_auth,
        record.policy_outcome.retrieval_allowed,
        retrieval_value >= thresholds.min_retrieval_value_for_retrieval_only or music_value >= 0.50,
        has_useful_descriptors,
    ]

    if all(retrieval_only_conditions):
        reason = "retrieval_useful_but_training_blocked"
        if low_transcription and has_useful_descriptors:
            reason = "low_transcription_but_retrieval_useful"
        return PromotionDecision(
            promotion_label="retrieval_only",
            reason=reason,
            blockers=sorted(set(blockers)),
            confidence=0.85,
        )

    return PromotionDecision(
        promotion_label="excluded",
        reason="insufficient_policy_or_music_value",
        blockers=sorted(set(blockers)),
        confidence=0.9,
    )
