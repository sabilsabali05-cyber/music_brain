from __future__ import annotations

from features.cloud_execution.cloud_backend_schema import CloudBackendConfig, CloudProviderConfig
from features.cloud_execution.cloud_execution_policy import evaluate_cloud_execution_request
from features.cloud_execution.cloud_job_schema import CloudJobRequest


def _backend(*, cloud_enabled: bool, dry_run_only: bool) -> CloudBackendConfig:
    provider = CloudProviderConfig(
        provider_id="modal",
        enabled=True,
        allow_cloud_execution=True,
        allow_upload=True,
        dry_run_only=False,
        api_base_url="https://api.modal.com",
        required_env_vars=[],
    )
    return CloudBackendConfig(
        manifest_version=1,
        cloud_enabled=cloud_enabled,
        dry_run_only=dry_run_only,
        default_budget_usd=0.0,
        providers={"modal": provider},
        source_path="config/cloud_backends/cloud_backends.local.json",
        using_local_config=True,
    )


def _backend_without_local() -> CloudBackendConfig:
    provider = CloudProviderConfig(
        provider_id="modal",
        enabled=True,
        allow_cloud_execution=True,
        allow_upload=True,
        dry_run_only=False,
        api_base_url="https://api.modal.com",
        required_env_vars=[],
    )
    return CloudBackendConfig(
        manifest_version=1,
        cloud_enabled=True,
        dry_run_only=False,
        default_budget_usd=0.0,
        providers={"modal": provider},
        source_path="config/cloud_backends/cloud_backends.example.json",
        using_local_config=False,
    )


def _job(**overrides: object) -> CloudJobRequest:
    payload = {
        "stage_name": "source_separation_demucs",
        "task_type": "demucs_source_separation",
        "provider_id": "modal",
        "model_id": "demucs",
        "input_id": "i1",
        "execute": False,
        "allow_cloud_execution": False,
        "allow_upload": False,
        "authorization_status": "unknown",
        "explicitly_authorized_for_execution": False,
        "requested_budget_usd": 0.0,
        "estimated_cost_usd": 1.0,
        "metadata": {},
    }
    payload.update(overrides)
    return CloudJobRequest(**payload)


def test_policy_blocks_when_cloud_disabled() -> None:
    decision = evaluate_cloud_execution_request(backend_config=_backend(cloud_enabled=False, dry_run_only=False), job=_job(), provider_available=True)
    assert decision.allowed is False
    assert "skipped_cloud_disabled" in decision.skip_reasons


def test_policy_requires_local_config() -> None:
    decision = evaluate_cloud_execution_request(backend_config=_backend_without_local(), job=_job(), provider_available=True)
    assert decision.allowed is False
    assert "skipped_missing_local_cloud_config" in decision.skip_reasons


def test_policy_requires_execute_allow_auth_and_budget() -> None:
    decision = evaluate_cloud_execution_request(
        backend_config=_backend(cloud_enabled=True, dry_run_only=False),
        job=_job(
            execute=True,
            allow_cloud_execution=True,
            allow_upload=True,
            explicitly_authorized_for_execution=True,
            authorization_status="authorized_for_processing",
            requested_budget_usd=5.0,
            estimated_cost_usd=1.0,
        ),
        provider_available=True,
    )
    assert decision.allowed is True
    assert decision.skip_reasons == []


def test_policy_blocks_when_budget_exceeded() -> None:
    decision = evaluate_cloud_execution_request(
        backend_config=_backend(cloud_enabled=True, dry_run_only=False),
        job=_job(
            execute=True,
            allow_cloud_execution=True,
            allow_upload=True,
            explicitly_authorized_for_execution=True,
            authorization_status="authorized_for_processing",
            requested_budget_usd=0.5,
            estimated_cost_usd=2.0,
        ),
        provider_available=True,
    )
    assert decision.allowed is False
    assert "skipped_budget" in decision.skip_reasons


def test_policy_blocks_training_jobs() -> None:
    decision = evaluate_cloud_execution_request(
        backend_config=_backend(cloud_enabled=True, dry_run_only=False),
        job=_job(task_type="train_musicbert_model"),
        provider_available=True,
    )
    assert decision.allowed is False
    assert "skipped_training_not_allowed_in_branch" in decision.skip_reasons
