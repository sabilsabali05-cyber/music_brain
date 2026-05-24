from __future__ import annotations

from typing import Any

from features.cloud_execution.cloud_job_schema import CloudJobResult


def describe_task() -> dict[str, Any]:
    return {
        "task_type": "demucs_source_separation",
        "model_id": "demucs",
        "evidence_policy": "source_separation=weak_evidence_not_truth",
    }


def estimate_cost(input_payload: dict[str, Any]) -> float:
    duration = float(input_payload.get("duration_seconds", 0.0))
    return round((duration / 60.0) * 0.05, 4)


def validate_inputs(input_payload: dict[str, Any]) -> tuple[bool, str]:
    if not input_payload.get("input_id"):
        return False, "missing_input_id"
    return True, "ok"


def plan_job(input_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_type": "demucs_source_separation",
        "input_id": input_payload.get("input_id", "unknown"),
        "estimated_cost_usd": estimate_cost(input_payload),
        "planned_only": True,
    }


def run_job(input_payload: dict[str, Any]) -> CloudJobResult:
    if not bool(input_payload.get("execute", False)):
        return CloudJobResult(
            status="skipped_dry_run",
            reason="execute_false",
            task_type="demucs_source_separation",
            provider_id=str(input_payload.get("provider_id", "unknown")),
            model_id="demucs",
            input_id=str(input_payload.get("input_id", "unknown")),
        )
    return CloudJobResult(
        status="skipped_unauthorized",
        reason="adapter_requires_external_policy_gate",
        task_type="demucs_source_separation",
        provider_id=str(input_payload.get("provider_id", "unknown")),
        model_id="demucs",
        input_id=str(input_payload.get("input_id", "unknown")),
    )
