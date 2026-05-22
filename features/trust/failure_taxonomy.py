from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

FAILURE_CATEGORIES = {
    "source_failure",
    "decode_failure",
    "analysis_failure",
    "segmentation_failure",
    "transcription_failure",
    "stitching_failure",
    "validation_failure",
    "dependency_unavailable",
    "external_model_failure",
    "model_disagreement",
    "low_signal",
    "ambiguous_label",
    "overmatch_risk",
    "schema_failure",
    "provenance_failure",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_failure_record(
    stage: str,
    category: str,
    severity: str,
    message: str,
    artifact_path: str | None = None,
    recoverable: bool = True,
    next_action: str | None = None,
) -> dict[str, Any]:
    normalized_category = category if category in FAILURE_CATEGORIES else "schema_failure"
    normalized_severity = severity if severity in {"info", "warning", "critical"} else "warning"
    return {
        "stage": stage,
        "category": normalized_category,
        "severity": normalized_severity,
        "message": message,
        "artifact_path": artifact_path,
        "recoverable": bool(recoverable),
        "next_action": next_action,
        "created_at": now_iso(),
    }
