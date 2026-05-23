from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

RouteStatus = Literal["allow_train", "allow_review_only", "block"]


@dataclass
class TrainingRouteDecision:
    status: RouteStatus
    reason: str
    train_allowed: bool
    review_allowed: bool


def _contains_splice(record: dict[str, Any]) -> bool:
    source_type = str(record.get("source_type", "")).lower()
    source_policy = str(record.get("source_policy", "")).lower()
    return "splice" in source_type or "splice" in source_policy


def _authorized_for_training(record: dict[str, Any]) -> bool:
    authorization = str(record.get("authorization_status", "")).lower()
    source_policy = str(record.get("source_policy", "")).lower()
    if source_policy == "user_owned_training_candidate":
        return True
    return authorization in {"trusted_for_training", "approved_for_training", "authorized_for_training"}


def _unknown_authorization(record: dict[str, Any]) -> bool:
    authorization = str(record.get("authorization_status", "")).strip().lower()
    source_policy = str(record.get("source_policy", "")).strip().lower()
    return authorization in {"", "unknown", "undeclared"} or source_policy in {"unknown_blocked", "unknown"}


def _synplant_inherits_restrictions(record: dict[str, Any]) -> bool:
    derived_type = str(record.get("derived_type", "")).lower()
    if "synplant" not in derived_type and str(record.get("model_origin", "")).lower() != "synplant":
        return True
    seed_policy = str(record.get("seed_source_policy", "")).lower()
    current_policy = str(record.get("source_policy", "")).lower()
    if seed_policy in {"splice_production_only", "production_only_training_excluded"}:
        return current_policy in {"splice_production_only", "production_only_training_excluded"}
    return True


def route_record_for_training(record: dict[str, Any]) -> TrainingRouteDecision:
    if _contains_splice(record):
        return TrainingRouteDecision(
            status="block",
            reason="splice_source_production_only_training_excluded",
            train_allowed=False,
            review_allowed=False,
        )

    if not _synplant_inherits_restrictions(record):
        return TrainingRouteDecision(
            status="block",
            reason="synplant_output_policy_violation_seed_restriction_not_inherited",
            train_allowed=False,
            review_allowed=False,
        )

    if _unknown_authorization(record):
        return TrainingRouteDecision(
            status="block",
            reason="unknown_authorization_blocks_training",
            train_allowed=False,
            review_allowed=False,
        )

    review_required = bool(record.get("requires_human_review", False))
    if review_required:
        return TrainingRouteDecision(
            status="allow_review_only",
            reason="review_required_before_train_split",
            train_allowed=False,
            review_allowed=True,
        )

    if _authorized_for_training(record):
        return TrainingRouteDecision(
            status="allow_train",
            reason="authorized_for_training",
            train_allowed=True,
            review_allowed=True,
        )

    return TrainingRouteDecision(
        status="allow_review_only",
        reason="not_authorized_for_training_but_review_allowed",
        train_allowed=False,
        review_allowed=True,
    )


def puredata_output_training_candidate(record: dict[str, Any]) -> bool:
    model_origin = str(record.get("model_origin", "")).lower()
    if model_origin not in {"pure_data", "pd", "max_pd_bridge"}:
        return False
    if _contains_splice(record):
        return False
    return _authorized_for_training(record)


def feedback_record_can_train_preference(record: dict[str, Any]) -> bool:
    feedback_type = str(record.get("feedback_type", "")).lower()
    accepted = record.get("accepted")
    if feedback_type in {"ableton_review", "candidate_review", "session_rating", "workflow_feedback"}:
        return isinstance(accepted, bool) or str(record.get("rating", "")).strip() != ""
    return False
