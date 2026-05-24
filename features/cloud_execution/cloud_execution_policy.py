from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from features.cloud_execution.cloud_backend_schema import CloudBackendConfig
from features.cloud_execution.cloud_job_schema import CloudJobRequest, SUPPORTED_TASK_TYPES

ALLOWED_AUTHORIZATION = {
    "authorized_for_processing",
    "approved_for_processing",
    "authorized_user_owned",
}


@dataclass(frozen=True)
class CloudExecutionDecision:
    allowed: bool
    reason: str
    skip_reasons: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_cloud_execution_request(
    *,
    backend_config: CloudBackendConfig,
    job: CloudJobRequest,
    provider_available: bool,
) -> CloudExecutionDecision:
    skip_reasons: list[str] = []
    if job.task_type not in SUPPORTED_TASK_TYPES:
        skip_reasons.append("skipped_task_type_not_supported")
    if "train" in job.task_type:
        skip_reasons.append("skipped_training_not_allowed_in_branch")
    if not backend_config.cloud_enabled:
        skip_reasons.append("skipped_cloud_disabled")
    if backend_config.dry_run_only:
        skip_reasons.append("skipped_dry_run_only")
    if not backend_config.using_local_config:
        skip_reasons.append("skipped_missing_local_cloud_config")
    if not job.execute:
        skip_reasons.append("skipped_execute_false")
    if not job.allow_cloud_execution:
        skip_reasons.append("skipped_unauthorized_allow_cloud_execution_false")
    if not job.explicitly_authorized_for_execution:
        skip_reasons.append("skipped_unauthorized_not_explicitly_authorized")
    if job.authorization_status.strip().lower() not in ALLOWED_AUTHORIZATION:
        skip_reasons.append("skipped_unauthorized_input_status")
    if not provider_available:
        skip_reasons.append("skipped_unavailable")
    if job.estimated_cost_usd > job.requested_budget_usd:
        skip_reasons.append("skipped_budget")
    if not job.allow_upload:
        skip_reasons.append("skipped_cloud_upload_not_allowed")
    if skip_reasons:
        return CloudExecutionDecision(allowed=False, reason=skip_reasons[0], skip_reasons=skip_reasons)
    return CloudExecutionDecision(allowed=True, reason="allowed", skip_reasons=[])


def summarize_policy_limits() -> dict[str, Any]:
    return {
        "cloud_disabled_by_default": True,
        "no_cloud_without_execute_and_allow": True,
        "no_cloud_without_authorized_input": True,
        "no_cloud_without_budget": True,
        "no_training_jobs_in_this_branch": True,
    }
