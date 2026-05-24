from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.cloud_execution.cloud_backend_schema import load_cloud_backend_config
from features.cloud_execution.cloud_provider_registry import evaluate_all_providers
from scripts.cloud_full_activation_common import CLOUD_REPORTS_DIR, REQUIRED_FALSE_FLAGS, now_iso, write_public_report


def build_cloud_backend_status() -> dict[str, object]:
    backend = load_cloud_backend_config()
    providers = evaluate_all_providers(backend)
    env_presence = {
        "modal_auth_present": bool(os.environ.get("MODAL_TOKEN_ID")) and bool(os.environ.get("MODAL_TOKEN_SECRET")),
        "hf_auth_present": bool(os.environ.get("HF_TOKEN")),
        "replicate_auth_present": bool(os.environ.get("REPLICATE_API_TOKEN")),
    }
    provider_rows = {provider_id: row.as_dict() for provider_id, row in providers.items()}
    return {
        "status": "ok",
        "created_at": now_iso(),
        "cloud_execution_available": any(row.available for row in providers.values()),
        "cloud_config_source": backend.source_path,
        "cloud_enabled": backend.cloud_enabled,
        "dry_run_only": backend.dry_run_only,
        "providers": provider_rows,
        "provider_available_flags": {
            "modal": bool(provider_rows.get("modal", {}).get("available", False)),
            "hf": bool(provider_rows.get("huggingface", {}).get("available", False)),
            "replicate": bool(provider_rows.get("replicate", {}).get("available", False)),
        },
        "env_var_presence_only": env_presence,
        "missing_secret_names": {provider_id: row.missing_secret_names for provider_id, row in providers.items()},
        **REQUIRED_FALSE_FLAGS,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check cloud backends without calling cloud APIs.")
    parser.add_argument("--output-dir", default=CLOUD_REPORTS_DIR.as_posix())
    args = parser.parse_args()
    payload = build_cloud_backend_status()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT_DIR / output_dir
    json_path = output_dir / "cloud_backend_status.json"
    md_path = output_dir / "cloud_backend_status.md"
    write_public_report(
        payload=payload,
        json_path=json_path,
        md_path=md_path,
        title="Cloud Backend Status",
        bullets=[
            f"cloud_execution_available: `{payload['cloud_execution_available']}`",
            f"dry_run_only: `{payload['dry_run_only']}`",
            f"cloud_jobs_started: `{payload['cloud_jobs_started']}`",
            f"uploads_performed: `{payload['uploads_performed']}`",
            f"downloads_performed: `{payload['downloads_performed']}`",
        ],
    )
    print(f"CLOUD_BACKEND_STATUS_JSON={json_path.as_posix()}")
    print(f"CLOUD_BACKEND_STATUS_MD={md_path.as_posix()}")
    print(f"CLOUD_EXECUTION_AVAILABLE={payload['cloud_execution_available']}")
    print(f"MODAL_AVAILABLE={payload['provider_available_flags']['modal']}")
    print(f"HF_AVAILABLE={payload['provider_available_flags']['hf']}")
    print(f"REPLICATE_AVAILABLE={payload['provider_available_flags']['replicate']}")
    print("CLOUD_JOBS_STARTED=False")
    print("UPLOADS_PERFORMED=False")
    print("DOWNLOADS_PERFORMED=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
