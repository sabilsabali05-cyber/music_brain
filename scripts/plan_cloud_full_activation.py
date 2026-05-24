from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.cloud_execution.cloud_backend_schema import load_cloud_backend_config
from features.cloud_execution.cloud_execution_policy import summarize_policy_limits
from features.cloud_execution.cloud_provider_registry import evaluate_all_providers
from scripts.check_model_integrations import evaluate_model_integrations
from scripts.cloud_full_activation_common import CLOUD_REPORTS_DIR, REQUIRED_FALSE_FLAGS, now_iso, write_public_report

STAGE_MODEL_MAP: list[tuple[str, str | None]] = [
    ("source_separation_demucs", "demucs"),
    ("audio_embedding_essentia", "essentia"),
    ("audio_embedding_muq", "muq"),
    ("audio_embedding_mert", "mert"),
    ("transcription_witness_yourmt3", "yourmt3"),
    ("transcription_witness_basic_pitch", "basic_pitch"),
    ("symbolic_generation_text2midi", "text2midi"),
    ("symbolic_generation_moonbeam", "moonbeam"),
    ("symbolic_generation_midigpt", "midigpt"),
    ("ranking_musicbert", "musicbert"),
    ("voice_interaction_graph", None),
    ("ableton_review_export_plan", None),
    ("ableton_export", None),
    ("training", None),
]


def _model_rows() -> dict[str, dict[str, Any]]:
    rows = evaluate_model_integrations().get("models", [])
    return {str(row.get("model_id", "")): row for row in rows if isinstance(row, dict)}


def _manifest_errors(manifest: dict[str, Any], backend_cloud_available: bool) -> list[str]:
    errors: list[str] = []
    if int(manifest.get("manifest_version", 0)) != 2:
        errors.append("manifest_version_must_be_2")
    if bool(manifest.get("execute", False)) and not bool(manifest.get("allow_cloud_execution", False)):
        errors.append("execute_requires_allow_cloud_execution")
    if bool(manifest.get("training_allowed", False)):
        errors.append("training_jobs_not_supported_in_this_branch")
    auth = manifest.get("input_authorization", {})
    auth = auth if isinstance(auth, dict) else {}
    if bool(manifest.get("execute", False)) and not bool(auth.get("explicitly_authorized_for_execution", False)):
        errors.append("execute_requires_explicit_input_authorization")
    if bool(manifest.get("allow_cloud_execution", False)) and not backend_cloud_available:
        errors.append("allow_cloud_execution_true_but_no_provider_available")
    return errors


def build_cloud_full_activation_plan(manifest: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    backend = load_cloud_backend_config()
    provider_status = evaluate_all_providers(backend)
    model_rows = _model_rows()
    model_cfg = manifest.get("models", {})
    model_cfg = model_cfg if isinstance(model_cfg, dict) else {}
    budget = float(manifest.get("max_budget_usd", 0.0))
    provider_available = {key: row.available for key, row in provider_status.items()}
    errors = _manifest_errors(manifest, any(provider_available.values()))

    stage_plan: list[dict[str, Any]] = []
    for stage_name, model_id in STAGE_MODEL_MAP:
        if stage_name == "training":
            stage_plan.append(
                {
                    "stage": stage_name,
                    "mode": "blocked",
                    "status": "skipped_training_not_allowed",
                    "reason": "training_jobs_not_supported_in_this_branch",
                }
            )
            continue
        if model_id is None:
            stage_plan.append({"stage": stage_name, "mode": "local_plan_only", "status": "planned_dry_run", "reason": "no_execution"})
            continue
        cfg = model_cfg.get(model_id, {})
        cfg = cfg if isinstance(cfg, dict) else {}
        requested = bool(cfg.get("enabled", False))
        provider = str(cfg.get("provider", "modal"))
        integration = model_rows.get(model_id, {})
        available = bool(integration.get("available", False))
        reason = str(integration.get("reason", "not_listed"))
        if not requested:
            status = "skipped_not_requested"
            reason = "manifest_model_disabled"
            mode = "none"
        elif not provider_available.get(provider, False):
            status = "skipped_unavailable"
            mode = "cloud"
            reason = f"provider_unavailable:{provider}"
        elif not available:
            status = "skipped_unavailable"
            mode = "local_or_cloud"
        elif budget <= 0:
            status = "skipped_budget"
            mode = "cloud"
            reason = "max_budget_usd_must_be_positive_for_execution"
        else:
            status = "planned_dry_run"
            mode = "cloud"
            reason = "execute_false_or_dry_run_defaults"
        stage_plan.append(
            {
                "stage": stage_name,
                "model_id": model_id,
                "provider": provider,
                "mode": mode,
                "status": status,
                "reason": reason,
                "integration_available": available,
            }
        )

    return {
        "status": "planned_dry_run",
        "created_at": now_iso(),
        "manifest_path": manifest_path.as_posix(),
        "manifest_version": manifest.get("manifest_version", 0),
        "execute": bool(manifest.get("execute", False)),
        "allow_cloud_execution": bool(manifest.get("allow_cloud_execution", False)),
        "allow_cloud_upload": bool(manifest.get("allow_cloud_upload", False)),
        "max_budget_usd": budget,
        "validation_errors": errors,
        "validation_passed": not errors,
        "providers": {key: row.as_dict() for key, row in provider_status.items()},
        "policy_limits": summarize_policy_limits(),
        "stage_plan": stage_plan,
        "provenance_outputs": [],
        "no_fake_output_guarantee": True,
        **REQUIRED_FALSE_FLAGS,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan cloud full activation without running cloud or local jobs.")
    parser.add_argument("manifest", help="Path to full cloud activation manifest.")
    parser.add_argument("--output-dir", default=CLOUD_REPORTS_DIR.as_posix())
    args = parser.parse_args()
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = ROOT_DIR / manifest_path
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload = build_cloud_full_activation_plan(manifest, manifest_path)
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT_DIR / output_dir
    json_path = output_dir / "cloud_full_activation_plan.json"
    md_path = output_dir / "cloud_full_activation_plan.md"
    write_public_report(
        payload=payload,
        json_path=json_path,
        md_path=md_path,
        title="Cloud Full Activation Plan",
        bullets=[
            f"status: `{payload['status']}`",
            f"validation_passed: `{payload['validation_passed']}`",
            f"cloud_jobs_started: `{payload['cloud_jobs_started']}`",
            f"uploads_performed: `{payload['uploads_performed']}`",
            f"downloads_performed: `{payload['downloads_performed']}`",
        ],
    )
    print(f"CLOUD_FULL_ACTIVATION_PLAN_JSON={json_path.as_posix()}")
    print(f"CLOUD_FULL_ACTIVATION_PLAN_MD={md_path.as_posix()}")
    print(f"CLOUD_FULL_ACTIVATION_PLAN_STATUS={payload['status']}")
    print("CLOUD_JOBS_STARTED=False")
    print("UPLOADS_PERFORMED=False")
    print("DOWNLOADS_PERFORMED=False")
    print("AUDIO_PROCESSING_PERFORMED=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
