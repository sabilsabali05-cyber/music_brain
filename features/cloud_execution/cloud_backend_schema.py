from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
LOCAL_PATH = ROOT_DIR / "config" / "cloud_backends" / "cloud_backends.local.json"
EXAMPLE_PATH = ROOT_DIR / "config" / "cloud_backends" / "cloud_backends.example.json"


@dataclass(frozen=True)
class CloudProviderConfig:
    provider_id: str
    enabled: bool
    allow_cloud_execution: bool
    allow_upload: bool
    dry_run_only: bool
    api_base_url: str
    required_env_vars: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "enabled": self.enabled,
            "allow_cloud_execution": self.allow_cloud_execution,
            "allow_upload": self.allow_upload,
            "dry_run_only": self.dry_run_only,
            "api_base_url": self.api_base_url,
            "required_env_vars": list(self.required_env_vars),
        }


@dataclass(frozen=True)
class CloudBackendConfig:
    manifest_version: int
    cloud_enabled: bool
    dry_run_only: bool
    default_budget_usd: float
    providers: dict[str, CloudProviderConfig]
    source_path: str
    using_local_config: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "cloud_enabled": self.cloud_enabled,
            "dry_run_only": self.dry_run_only,
            "default_budget_usd": self.default_budget_usd,
            "providers": {key: row.as_dict() for key, row in self.providers.items()},
            "source_path": self.source_path,
            "using_local_config": self.using_local_config,
        }


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


def _provider_from_row(provider_id: str, row: dict[str, Any]) -> CloudProviderConfig:
    return CloudProviderConfig(
        provider_id=provider_id,
        enabled=bool(row.get("enabled", False)),
        allow_cloud_execution=bool(row.get("allow_cloud_execution", False)),
        allow_upload=bool(row.get("allow_upload", False)),
        dry_run_only=bool(row.get("dry_run_only", True)),
        api_base_url=str(row.get("api_base_url", "")),
        required_env_vars=[str(item) for item in row.get("required_env_vars", []) if isinstance(item, str)],
    )


def load_cloud_backend_config() -> CloudBackendConfig:
    source_path = LOCAL_PATH if LOCAL_PATH.exists() else EXAMPLE_PATH
    payload = _load_json(source_path)
    providers_payload = payload.get("providers", {})
    providers_payload = providers_payload if isinstance(providers_payload, dict) else {}
    providers = {
        provider_id: _provider_from_row(provider_id, row if isinstance(row, dict) else {})
        for provider_id, row in providers_payload.items()
    }
    return CloudBackendConfig(
        manifest_version=int(payload.get("manifest_version", 1)),
        cloud_enabled=bool(payload.get("cloud_enabled", False)),
        dry_run_only=bool(payload.get("dry_run_only", True)),
        default_budget_usd=float(payload.get("default_budget_usd", 0.0)),
        providers=providers,
        source_path=source_path.as_posix(),
        using_local_config=source_path == LOCAL_PATH,
    )
