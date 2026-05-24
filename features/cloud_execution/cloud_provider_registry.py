from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Any

from features.cloud_execution.cloud_backend_schema import CloudBackendConfig, CloudProviderConfig

ENV_ALIAS_MAP = {
    "modal_token_id": "MODAL_TOKEN_ID",
    "modal_token_secret": "MODAL_TOKEN_SECRET",
    "hf_token": "HF_TOKEN",
    "replicate_api_token": "REPLICATE_API_TOKEN",
}


@dataclass(frozen=True)
class CloudProviderStatus:
    provider_id: str
    configured: bool
    available: bool
    dry_run_only: bool
    missing_secret_names: list[str]
    allow_cloud_execution: bool
    allow_upload: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_provider_status(provider_id: str, provider: CloudProviderConfig) -> CloudProviderStatus:
    missing = []
    for name in provider.required_env_vars:
        env_key = ENV_ALIAS_MAP.get(name, name)
        if not os.environ.get(env_key):
            missing.append(name)
    configured = provider.enabled
    available = configured and not missing and provider.allow_cloud_execution and not provider.dry_run_only
    return CloudProviderStatus(
        provider_id=provider_id,
        configured=configured,
        available=available,
        dry_run_only=provider.dry_run_only,
        missing_secret_names=missing,
        allow_cloud_execution=provider.allow_cloud_execution,
        allow_upload=provider.allow_upload,
    )


def evaluate_all_providers(backend_config: CloudBackendConfig) -> dict[str, CloudProviderStatus]:
    return {
        provider_id: evaluate_provider_status(provider_id, provider)
        for provider_id, provider in backend_config.providers.items()
    }
