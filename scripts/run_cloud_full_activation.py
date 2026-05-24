from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.cloud_execution.cloud_artifact_policy import verify_artifact_provenance
from features.cloud_execution.cloud_backend_schema import load_cloud_backend_config
from features.cloud_execution.cloud_execution_policy import evaluate_cloud_execution_request, summarize_policy_limits
from features.cloud_execution.cloud_job_schema import CloudJobRequest
from features.cloud_execution.cloud_provider_registry import evaluate_all_providers
from features.cloud_execution.task_adapters import (
    basic_pitch_cloud_task,
    demucs_cloud_task,
    essentia_cloud_task,
    mert_cloud_task,
    midigpt_cloud_task,
    moonbeam_cloud_task,
    muq_cloud_task,
    musicbert_cloud_task,
    text2midi_cloud_task,
    yourmt3_cloud_task,
)
from scripts.check_model_integrations import evaluate_model_integrations
from scripts.cloud_full_activation_common import CLOUD_REPORTS_DIR, REQUIRED_FALSE_FLAGS, now_iso, write_public_report

TASKS = [
    ("source_separation_demucs", "demucs", "demucs_source_separation", demucs_cloud_task),
    ("audio_embedding_essentia", "essentia", "essentia_embedding", essentia_cloud_task),
    ("audio_embedding_muq", "muq", "muq_embedding", muq_cloud_task),
    ("audio_embedding_mert", "mert", "mert_embedding", mert_cloud_task),
    ("transcription_witness_yourmt3", "yourmt3", "yourmt3_transcription_witness", yourmt3_cloud_task),
    ("transcription_witness_basic_pitch", "basic_pitch", "basic_pitch_transcription_witness", basic_pitch_cloud_task),
    ("symbolic_generation_text2midi", "text2midi", "text2midi_symbolic_generation", text2midi_cloud_task),
    ("symbolic_generation_moonbeam", "moonbeam", "moonbeam_symbolic_generation", moonbeam_cloud_task),
    ("symbolic_generation_midigpt", "midigpt", "midigpt_symbolic_generation", midigpt_cloud_task),
    ("ranking_musicbert", "musicbert", "musicbert_ranking", musicbert_cloud_task),
]


def _integration_rows() -> dict[str, dict[str, Any]]:
    rows = evaluate_model_integrations().get("models", [])
    return {str(row.get("model_id", "")): row for row in rows if isinstance(row, dict)}


def _canonical_skip_status(skip_reasons: list[str]) -> str:
    if any(reason.startswith("skipped_unavailable") for reason in skip_reasons):
        return "skipped_unavailable"
    if "skipped_budget" in skip_reasons:
        return "skipped_budget"
    if "skipped_cloud_upload_not_allowed" in skip_reasons:
        return "skipped_cloud_upload_not_allowed"
    if any(reason.startswith("skipped_unauthorized") for reason in skip_reasons):
        return "skipped_unauthorized"
    return skip_reasons[0] if skip_reasons else "skipped_unknown"


def build_cloud_full_activation_run_report(manifest: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    backend = load_cloud_backend_config()
    providers = evaluate_all_providers(backend)
    integrations = _integration_rows()
    inputs = manifest.get("inputs", [])
    inputs = inputs if isinstance(inputs, list) and inputs else [{"input_id": "missing_input"}]
    first_input = inputs[0] if isinstance(inputs[0], dict) else {"input_id": "invalid_input"}
    auth = manifest.get("input_authorization", {})
    auth = auth if isinstance(auth, dict) else {}
    budget = float(manifest.get("max_budget_usd", 0.0))
    models = manifest.get("models", {})
    models = models if isinstance(models, dict) else {}

    stage_results: list[dict[str, Any]] = []
    for stage_name, model_id, task_type, adapter in TASKS:
        model_cfg = models.get(model_id, {})
        model_cfg = model_cfg if isinstance(model_cfg, dict) else {}
        requested = bool(model_cfg.get("enabled", False))
        provider_id = str(model_cfg.get("provider", "modal"))
        provider_status = providers.get(provider_id)
        integration = integrations.get(model_id, {})
        if not requested:
            stage_results.append(
                {
                    "stage": stage_name,
                    "model_id": model_id,
                    "status": "skipped_not_requested",
                    "reason": "manifest_model_disabled",
                }
            )
            continue
        if provider_status is None:
            stage_results.append(
                {"stage": stage_name, "model_id": model_id, "status": "skipped_unavailable", "reason": "provider_not_registered"}
            )
            continue
        job = CloudJobRequest(
            stage_name=stage_name,
            task_type=task_type,
            provider_id=provider_id,
            model_id=model_id,
            input_id=str(first_input.get("input_id", "unknown_input")),
            execute=bool(manifest.get("execute", False)),
            allow_cloud_execution=bool(manifest.get("allow_cloud_execution", False)),
            allow_upload=bool(manifest.get("allow_cloud_upload", False)),
            authorization_status=str(auth.get("authorization_status", "unknown")),
            explicitly_authorized_for_execution=bool(auth.get("explicitly_authorized_for_execution", False)),
            requested_budget_usd=budget,
            estimated_cost_usd=float(adapter.estimate_cost(first_input)),
            metadata={},
        )
        decision = evaluate_cloud_execution_request(
            backend_config=backend,
            job=job,
            provider_available=provider_status.available and bool(integration.get("available", False)),
        )
        if not decision.allowed:
            reason = _canonical_skip_status(decision.skip_reasons)
            stage_results.append(
                {
                    "stage": stage_name,
                    "model_id": model_id,
                    "status": reason,
                    "skip_reasons": decision.skip_reasons,
                }
            )
            continue
        adapter_result = adapter.run_job({"execute": job.execute, "provider_id": provider_id, "input_id": job.input_id}).as_dict()
        provenance_ok, provenance_reason = verify_artifact_provenance(adapter_result.get("artifact_path"), {"producer_confirmed": False})
        stage_results.append(
            {
                "stage": stage_name,
                "model_id": model_id,
                "status": adapter_result["status"],
                "reason": adapter_result["reason"],
                "provenance_verified": provenance_ok,
                "provenance_reason": provenance_reason,
            }
        )

    stage_results.extend(
        [
            {"stage": "voice_interaction_graph", "status": "planned_no_evidence", "reason": "no_evidence_inputs"},
            {"stage": "ableton_review_export_plan", "status": "planned_only", "reason": "plan_stage_only"},
            {
                "stage": "ableton_export",
                "status": "skipped_cloud_upload_not_allowed"
                if not bool(manifest.get("allow_ableton_export", False))
                else "planned_only",
                "reason": "allow_ableton_export_false"
                if not bool(manifest.get("allow_ableton_export", False))
                else "evidence_required",
            },
            {"stage": "training", "status": "skipped_training_not_allowed", "reason": "training_jobs_not_supported_in_this_branch"},
        ]
    )

    run_status = "planned_dry_run" if not bool(manifest.get("execute", False)) else "gated_execute"
    return {
        "status": run_status,
        "created_at": now_iso(),
        "manifest_path": manifest_path.as_posix(),
        "manifest_version": manifest.get("manifest_version", 0),
        "execute": bool(manifest.get("execute", False)),
        "allow_cloud_execution": bool(manifest.get("allow_cloud_execution", False)),
        "allow_cloud_upload": bool(manifest.get("allow_cloud_upload", False)),
        "allow_ableton_export": bool(manifest.get("allow_ableton_export", False)),
        "validation_errors": ["training_jobs_not_supported_in_this_branch"]
        if bool(manifest.get("training_allowed", False))
        else [],
        "validation_passed": not bool(manifest.get("training_allowed", False)),
        "stage_results": stage_results,
        "policy_limits": summarize_policy_limits(),
        "provenance_outputs": [],
        "no_fake_output_guarantee": True,
        **REQUIRED_FALSE_FLAGS,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run cloud full activation with strict dry-run defaults.")
    parser.add_argument("manifest", help="Path to full cloud activation manifest.")
    parser.add_argument("--output-dir", default=CLOUD_REPORTS_DIR.as_posix())
    args = parser.parse_args()
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = ROOT_DIR / manifest_path
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload = build_cloud_full_activation_run_report(manifest, manifest_path)
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT_DIR / output_dir
    json_path = output_dir / "cloud_full_activation_run_report.json"
    md_path = output_dir / "cloud_full_activation_run_report.md"
    write_public_report(
        payload=payload,
        json_path=json_path,
        md_path=md_path,
        title="Cloud Full Activation Run Report",
        bullets=[
            f"status: `{payload['status']}`",
            f"validation_passed: `{payload['validation_passed']}`",
            f"cloud_jobs_started: `{payload['cloud_jobs_started']}`",
            f"uploads_performed: `{payload['uploads_performed']}`",
            f"downloads_performed: `{payload['downloads_performed']}`",
        ],
    )
    print(f"CLOUD_FULL_ACTIVATION_RUN_JSON={json_path.as_posix()}")
    print(f"CLOUD_FULL_ACTIVATION_RUN_MD={md_path.as_posix()}")
    print(f"CLOUD_FULL_ACTIVATION_RUN_STATUS={payload['status']}")
    print("CLOUD_JOBS_STARTED=False")
    print("UPLOADS_PERFORMED=False")
    print("DOWNLOADS_PERFORMED=False")
    print("AUDIO_PROCESSING_PERFORMED=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
