from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _base_feature_fields(
    *,
    performance_id: str,
    source_name: str,
    segment_run_id: str,
    window_id: str | None,
    start_seconds: float | None,
    end_seconds: float | None,
    duration_seconds: float | None,
    source_artifact_paths: dict[str, str | None],
    feature_version: str,
    extractor_name: str,
    confidence: float,
    limitations: list[str],
    created_at: str | None = None,
) -> dict[str, Any]:
    return {
        "performance_id": performance_id,
        "source_name": source_name,
        "segment_run_id": segment_run_id,
        "window_id": window_id,
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "duration_seconds": duration_seconds,
        "source_artifact_paths": source_artifact_paths,
        "feature_version": feature_version,
        "extractor_name": extractor_name,
        "confidence": round(float(confidence), 6),
        "limitations": list(limitations),
        "created_at": created_at or _now_iso(),
    }


def performance_feature_pack(
    *,
    performance_id: str,
    source_name: str,
    segment_run_id: str,
    source_artifact_paths: dict[str, str | None],
    feature_version: str,
    extractor_name: str,
    confidence: float,
    limitations: list[str],
    summary: dict[str, Any],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    payload = _base_feature_fields(
        performance_id=performance_id,
        source_name=source_name,
        segment_run_id=segment_run_id,
        window_id=None,
        start_seconds=None,
        end_seconds=None,
        duration_seconds=None,
        source_artifact_paths=source_artifact_paths,
        feature_version=feature_version,
        extractor_name=extractor_name,
        confidence=confidence,
        limitations=limitations,
    )
    payload["summary"] = summary
    payload["records"] = records
    return payload


def segment_feature_pack(
    *,
    performance_id: str,
    source_name: str,
    segment_run_id: str,
    start_seconds: float,
    end_seconds: float,
    duration_seconds: float,
    source_artifact_paths: dict[str, str | None],
    feature_version: str,
    extractor_name: str,
    confidence: float,
    limitations: list[str],
    segment_id: str,
    features: dict[str, Any],
) -> dict[str, Any]:
    payload = _base_feature_fields(
        performance_id=performance_id,
        source_name=source_name,
        segment_run_id=segment_run_id,
        window_id=None,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        duration_seconds=duration_seconds,
        source_artifact_paths=source_artifact_paths,
        feature_version=feature_version,
        extractor_name=extractor_name,
        confidence=confidence,
        limitations=limitations,
    )
    payload["segment_id"] = segment_id
    payload["features"] = features
    return payload


def window_feature_pack(
    *,
    performance_id: str,
    source_name: str,
    segment_run_id: str,
    window_id: str,
    start_seconds: float,
    end_seconds: float,
    duration_seconds: float,
    source_artifact_paths: dict[str, str | None],
    feature_version: str,
    extractor_name: str,
    confidence: float,
    limitations: list[str],
    features: dict[str, Any],
) -> dict[str, Any]:
    payload = _base_feature_fields(
        performance_id=performance_id,
        source_name=source_name,
        segment_run_id=segment_run_id,
        window_id=window_id,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        duration_seconds=duration_seconds,
        source_artifact_paths=source_artifact_paths,
        feature_version=feature_version,
        extractor_name=extractor_name,
        confidence=confidence,
        limitations=limitations,
    )
    payload["features"] = features
    return payload


def rhythm_feature_record(
    *,
    performance_id: str,
    source_name: str,
    segment_run_id: str,
    window_id: str | None,
    start_seconds: float | None,
    end_seconds: float | None,
    duration_seconds: float | None,
    source_artifact_paths: dict[str, str | None],
    confidence: float,
    limitations: list[str],
    features: dict[str, Any],
    feature_version: str = "rhythm_v1",
    extractor_name: str = "rhythm_feature_extractor_v1",
) -> dict[str, Any]:
    payload = _base_feature_fields(
        performance_id=performance_id,
        source_name=source_name,
        segment_run_id=segment_run_id,
        window_id=window_id,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        duration_seconds=duration_seconds,
        source_artifact_paths=source_artifact_paths,
        feature_version=feature_version,
        extractor_name=extractor_name,
        confidence=confidence,
        limitations=limitations,
    )
    payload["record_type"] = "rhythm_feature_record"
    payload["features"] = features
    return payload


def harmony_feature_record(
    *,
    performance_id: str,
    source_name: str,
    segment_run_id: str,
    window_id: str | None,
    start_seconds: float | None,
    end_seconds: float | None,
    duration_seconds: float | None,
    source_artifact_paths: dict[str, str | None],
    confidence: float,
    limitations: list[str],
    features: dict[str, Any],
    feature_version: str = "harmony_v1",
    extractor_name: str = "harmony_feature_extractor_v1",
) -> dict[str, Any]:
    payload = _base_feature_fields(
        performance_id=performance_id,
        source_name=source_name,
        segment_run_id=segment_run_id,
        window_id=window_id,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        duration_seconds=duration_seconds,
        source_artifact_paths=source_artifact_paths,
        feature_version=feature_version,
        extractor_name=extractor_name,
        confidence=confidence,
        limitations=limitations,
    )
    payload["record_type"] = "harmony_feature_record"
    payload["features"] = features
    return payload


def tag_record(
    *,
    performance_id: str,
    source_name: str,
    segment_run_id: str,
    window_id: str | None,
    start_seconds: float | None,
    end_seconds: float | None,
    duration_seconds: float | None,
    source_artifact_paths: dict[str, str | None],
    confidence: float,
    limitations: list[str],
    tag: str,
    evidence: dict[str, Any],
    feature_version: str = "tagging_v1",
    extractor_name: str = "feature_tagger_v1",
) -> dict[str, Any]:
    payload = _base_feature_fields(
        performance_id=performance_id,
        source_name=source_name,
        segment_run_id=segment_run_id,
        window_id=window_id,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        duration_seconds=duration_seconds,
        source_artifact_paths=source_artifact_paths,
        feature_version=feature_version,
        extractor_name=extractor_name,
        confidence=confidence,
        limitations=limitations,
    )
    payload["record_type"] = "tag_record"
    payload["tag"] = tag
    payload["evidence"] = evidence
    return payload


def ai_training_record(
    *,
    performance_id: str,
    source_name: str,
    segment_run_id: str,
    window_id: str | None,
    start_seconds: float | None,
    end_seconds: float | None,
    duration_seconds: float | None,
    source_artifact_paths: dict[str, str | None],
    confidence: float,
    limitations: list[str],
    label: str,
    input_features: dict[str, Any],
    feature_version: str = "ai_training_v1",
    extractor_name: str = "ai_training_record_builder_v1",
) -> dict[str, Any]:
    payload = _base_feature_fields(
        performance_id=performance_id,
        source_name=source_name,
        segment_run_id=segment_run_id,
        window_id=window_id,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        duration_seconds=duration_seconds,
        source_artifact_paths=source_artifact_paths,
        feature_version=feature_version,
        extractor_name=extractor_name,
        confidence=confidence,
        limitations=limitations,
    )
    payload["record_type"] = "ai_training_record"
    payload["label"] = label
    payload["input_features"] = input_features
    return payload
