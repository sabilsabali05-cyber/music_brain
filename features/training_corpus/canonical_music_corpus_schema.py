from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

CANONICAL_FIELDS = [
    "item_id",
    "source_artifact",
    "source_type",
    "source_path_redacted",
    "authorization_status",
    "training_allowed",
    "production_use_allowed",
    "retrieval_allowed",
    "review_status",
    "review_reason",
    "policy_status",
    "excluded_reason",
    "split",
    "human_rating",
    "keep_reject_label",
    "harmony_quality",
    "melody_quality",
    "rhythm_quality",
    "texture_quality",
    "arrangement_quality",
    "emotional_quality",
    "weirdness_quality",
    "musicality_quality",
    "tags",
    "provenance",
    "created_at",
    "normalized_at",
]

POLICY_REQUIRED_FIELDS = [
    "authorization_status",
    "training_allowed",
    "production_use_allowed",
    "retrieval_allowed",
    "review_status",
]

LABEL_FIELDS = [
    "human_rating",
    "keep_reject_label",
    "harmony_quality",
    "melody_quality",
    "rhythm_quality",
    "texture_quality",
    "arrangement_quality",
    "emotional_quality",
    "weirdness_quality",
    "musicality_quality",
]

_PRIVATE_PATH_PATTERNS = [
    re.compile(r"[A-Za-z]:[/\\]Users[/\\][^/\\]+", re.IGNORECASE),
    re.compile(r"/Users/[^/]+", re.IGNORECASE),
]


@dataclass(frozen=True)
class NormalizationStats:
    missing_policy_fields: list[str]
    missing_label_fields: list[str]
    schema_drift_resolved: bool


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _to_bool(value: Any, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y"}:
            return True
        if lowered in {"false", "0", "no", "n"}:
            return False
    return default


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None
    return None


def _parse_tags(value: Any) -> list[str]:
    if isinstance(value, list):
        tags: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                tags.append(item.strip())
            elif isinstance(item, dict):
                tag = item.get("tag")
                if isinstance(tag, str) and tag.strip():
                    tags.append(tag.strip())
        return sorted(set(tags))
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def redact_private_paths(value: Any) -> Any:
    if isinstance(value, str):
        redacted = value
        for pattern in _PRIVATE_PATH_PATTERNS:
            redacted = pattern.sub("<PRIVATE_LOCAL_PATH>", redacted)
        return redacted
    if isinstance(value, list):
        return [redact_private_paths(item) for item in value]
    if isinstance(value, dict):
        return {key: redact_private_paths(item) for key, item in value.items()}
    return value


def _normalize_status(value: Any, *, default: str) -> str:
    if not isinstance(value, str) or not value.strip():
        return default
    normalized = value.strip().lower()
    if normalized in {"accepted", "approve", "approved", "reviewed"}:
        return "accepted"
    if normalized in {"rejected", "reject", "deny", "denied", "excluded"}:
        return "rejected"
    if normalized in {"pending", "review_required", "review-required", "unknown"}:
        return "review_required"
    return normalized


def _resolve_item_id(row: dict[str, Any], source_artifact: str) -> str:
    for key in ("item_id", "record_id", "source_record_id", "export_record_id", "queue_id", "feedback_id"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    stable = f"{source_artifact}:{repr(sorted(row.items(), key=lambda item: item[0]))}"
    digest = hashlib.sha1(stable.encode("utf-8")).hexdigest()[:16]
    return f"generated_{digest}"


def _guess_source_path(row: dict[str, Any], source_artifact: str) -> str:
    for key in ("source_path", "audio_ref", "midi_ref", "merged_midi_ref", "target", "source_feature_pack_path"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return source_artifact


def _default_source_type(source_artifact: str) -> str:
    lowered = source_artifact.lower()
    if "training_exports" in lowered:
        return "training_export"
    if "review_queue" in lowered:
        return "review_queue"
    if "feedback" in lowered or "review_regen" in lowered:
        return "generated_midi_feedback"
    if "controlled_ingestion" in lowered or "ingestion" in lowered:
        return "ingestion_policy_report"
    return "artifact_record"


def _label_missing_fields(row: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for field in LABEL_FIELDS:
        value = row.get(field)
        if value is None or value == "":
            missing.append(field)
    return missing


def normalize_music_corpus_row(
    row: dict[str, Any],
    *,
    source_artifact: str,
    source_type: str | None = None,
    normalized_at: str | None = None,
) -> tuple[dict[str, Any], NormalizationStats]:
    raw = deepcopy(row)
    now = normalized_at or _now_iso()
    resolved_source_type = source_type or _default_source_type(source_artifact)

    split = str(raw.get("split", raw.get("export_split", "")) or "")
    split_lower = split.lower()
    inferred_review_status = "review_required"
    if "accepted" in split_lower:
        inferred_review_status = "accepted"
    elif "reject" in split_lower or "exclude" in split_lower:
        inferred_review_status = "rejected"

    review_status = _normalize_status(raw.get("review_status"), default=inferred_review_status)
    authorization_status = _normalize_status(
        raw.get("authorization_status", raw.get("authorization")),
        default=("accepted" if review_status == "accepted" else "review_required"),
    )
    if not split and review_status == "accepted":
        split = "train_candidate"

    explicit_training_present = "training_allowed" in raw
    training_allowed = _to_bool(raw.get("training_allowed"), default=False)
    production_use_allowed = _to_bool(raw.get("production_use_allowed", raw.get("production_only")), default=False)
    retrieval_allowed = _to_bool(raw.get("retrieval_allowed"), default=True)

    source_hint = f"{source_artifact} {raw.get('source_name', '')} {raw.get('source_record_id', '')}".lower()
    splice_or_production = ("splice" in source_hint) or _to_bool(raw.get("production_only"), default=False)
    if splice_or_production and not explicit_training_present:
        training_allowed = False
        retrieval_allowed = True

    if resolved_source_type == "generated_midi_feedback" and review_status != "accepted":
        training_allowed = False

    canonical: dict[str, Any] = {
        "item_id": _resolve_item_id(raw, source_artifact),
        "source_artifact": source_artifact,
        "source_type": resolved_source_type,
        "source_path_redacted": redact_private_paths(_guess_source_path(raw, source_artifact)),
        "authorization_status": authorization_status,
        "training_allowed": training_allowed,
        "production_use_allowed": production_use_allowed,
        "retrieval_allowed": retrieval_allowed,
        "review_status": review_status,
        "review_reason": raw.get("review_reason") or raw.get("inclusion_reason") or raw.get("confidence_reason") or "",
        "policy_status": "unknown",
        "excluded_reason": raw.get("excluded_reason") or "",
        "split": split,
        "human_rating": _to_float(raw.get("human_rating", raw.get("rating"))),
        "keep_reject_label": str(raw.get("keep_reject_label", "unlabeled")),
        "harmony_quality": _to_float(raw.get("harmony_quality")),
        "melody_quality": _to_float(raw.get("melody_quality")),
        "rhythm_quality": _to_float(raw.get("rhythm_quality")),
        "texture_quality": _to_float(raw.get("texture_quality")),
        "arrangement_quality": _to_float(raw.get("arrangement_quality")),
        "emotional_quality": _to_float(raw.get("emotional_quality")),
        "weirdness_quality": _to_float(raw.get("weirdness_quality")),
        "musicality_quality": _to_float(raw.get("musicality_quality")),
        "tags": _parse_tags(raw.get("tags") or raw.get("top_tags")),
        "provenance": redact_private_paths(
            raw.get("provenance")
            or {
                "source_record_id": raw.get("source_record_id") or raw.get("record_id"),
                "export_record_id": raw.get("export_record_id"),
                "confidence": raw.get("confidence"),
                "trust_tier": raw.get("trust_tier"),
            }
        ),
        "created_at": raw.get("created_at"),
        "normalized_at": now,
    }

    if canonical["keep_reject_label"] not in {"keep", "reject", "retrieval_only", "unlabeled"}:
        canonical["keep_reject_label"] = "unlabeled"

    missing_policy_fields = [field for field in POLICY_REQUIRED_FIELDS if canonical.get(field) in (None, "", "unknown")]
    if not explicit_training_present:
        missing_policy_fields.append("training_allowed")
    missing_policy_fields = sorted(set(missing_policy_fields))
    missing_label_fields = _label_missing_fields(canonical)

    canonical["policy_status"] = "missing_fields" if missing_policy_fields else "complete"
    if canonical["review_status"] == "rejected":
        canonical["excluded_reason"] = canonical["excluded_reason"] or "rejected"
    if canonical["review_status"] == "review_required" and not canonical["excluded_reason"]:
        canonical["excluded_reason"] = "review_required"
    if canonical["training_allowed"] is False and splice_or_production and not canonical["excluded_reason"]:
        canonical["excluded_reason"] = "production_or_splice_default_retrieval_only"

    drift_resolved = sorted(raw.keys()) != sorted(CANONICAL_FIELDS)
    return canonical, NormalizationStats(
        missing_policy_fields=missing_policy_fields,
        missing_label_fields=missing_label_fields,
        schema_drift_resolved=drift_resolved,
    )

