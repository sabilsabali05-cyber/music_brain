from __future__ import annotations

from typing import Any

from features.cloud_execution.cloud_job_schema import CloudJobResult


def describe_task() -> dict[str, Any]:
    return {"task_type": "muq_embedding", "model_id": "muq", "evidence_policy": "embeddings=semantic_evidence_not_truth"}


def estimate_cost(input_payload: dict[str, Any]) -> float:
    return round(float(input_payload.get("segment_count", 1)) * 0.015, 4)


def validate_inputs(input_payload: dict[str, Any]) -> tuple[bool, str]:
    return (bool(input_payload.get("input_id")), "ok" if input_payload.get("input_id") else "missing_input_id")


def plan_job(input_payload: dict[str, Any]) -> dict[str, Any]:
    return {"task_type": "muq_embedding", "estimated_cost_usd": estimate_cost(input_payload), "planned_only": True}


def run_job(input_payload: dict[str, Any]) -> CloudJobResult:
    return CloudJobResult(
        status="skipped_dry_run" if not bool(input_payload.get("execute", False)) else "skipped_unauthorized",
        reason="execute_false" if not bool(input_payload.get("execute", False)) else "adapter_requires_external_policy_gate",
        task_type="muq_embedding",
        provider_id=str(input_payload.get("provider_id", "unknown")),
        model_id="muq",
        input_id=str(input_payload.get("input_id", "unknown")),
    )
