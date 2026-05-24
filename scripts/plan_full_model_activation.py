from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.full_model_activation_common import (  # noqa: E402
    REPORTS_DIR,
    REQUIRED_DRY_RUN_FLAGS,
    model_rows_from_checker,
    normalized_model_config,
    now_iso,
    unauthorized_inputs,
    validate_manifest,
    write_report,
)


def _plan_stages(manifest: dict[str, Any], model_rows: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    model_cfg = normalized_model_config(manifest)
    allow_flags = manifest.get("allow_flags", {})
    allow_flags = allow_flags if isinstance(allow_flags, dict) else {}
    execute = bool(manifest.get("execute", False))
    stages = []

    stage_models: dict[str, list[str]] = {
        "source_separation": ["demucs"],
        "transcription": ["yourmt3", "basic_pitch"],
        "embeddings": ["muq", "mert", "essentia", "musicbert"],
        "symbolic_generation": ["moonbeam", "midigpt", "text2midi"],
    }

    for stage_name, model_ids in stage_models.items():
        rows = []
        for model_id in model_ids:
            requested = bool(model_cfg.get(model_id, {}).get("enabled", False))
            available_row = model_rows.get(model_id, {})
            available = bool(available_row.get("available", False))
            reason = str(available_row.get("reason", "not_listed_in_model_checker"))
            if not requested:
                status = "skipped_not_requested"
                reason = "manifest_model_disabled"
            elif not execute:
                status = "skipped_dry_run"
                reason = "execute_false_no_processing"
            elif not bool(allow_flags.get("allow_audio_processing", False)):
                status = "blocked_missing_allow_audio_processing"
                reason = "allow_flags.allow_audio_processing=false"
            elif not available:
                status = "skipped_unavailable"
            else:
                status = "planned_execution_path"
                reason = "configured_and_available_but_not_executed_by_planner"
            rows.append({"model_id": model_id, "status": status, "reason": reason, "available": available})
        stages.append({"stage_name": stage_name, "models": rows})

    training_stage = {
        "stage_name": "training_export",
        "models": [],
        "status": "blocked",
        "reason": "training_disabled_by_default",
    }
    if bool(manifest.get("export_training_dataset", False)):
        if bool(manifest.get("training_allowed", False)) and bool(manifest.get("human_review_required", False)):
            training_stage["status"] = "planned_review_gated_export_only"
            training_stage["reason"] = "requested_training_export_still_requires_manual_human_review"
        else:
            training_stage["reason"] = "training_export_requires_training_allowed_and_human_review_required"
    stages.append(training_stage)
    return stages


def build_activation_plan(manifest: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    validation = validate_manifest(manifest)
    model_rows = model_rows_from_checker()
    blocked_inputs = unauthorized_inputs(manifest)
    return {
        "status": "planned",
        "created_at": now_iso(),
        "manifest_path": manifest_path.as_posix(),
        "execute": bool(manifest.get("execute", False)),
        "validation_passed": validation.valid,
        "validation_errors": validation.errors,
        "validation_warnings": validation.warnings,
        "unauthorized_inputs": blocked_inputs,
        "config": {
            "local_model_config_exists": (ROOT_DIR / "config" / "model_integrations" / "model_integrations.local.json").exists(),
            "enabled_models_in_manifest": sorted(
                [model_id for model_id, row in normalized_model_config(manifest).items() if bool(row.get("enabled", False))]
            ),
        },
        "stage_plan": _plan_stages(manifest, model_rows),
        "training_export_authorized": bool(manifest.get("training_allowed", False))
        and bool(manifest.get("human_review_required", False)),
        **REQUIRED_DRY_RUN_FLAGS,
        "no_modal_calls_performed": True,
        "model_weights_downloaded": False,
        "provenance_outputs": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan full model activation without running models or audio processing.")
    parser.add_argument("manifest", help="Path to activation manifest JSON.")
    parser.add_argument("--output-dir", default=REPORTS_DIR.as_posix())
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = ROOT_DIR / manifest_path
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload = build_activation_plan(manifest, manifest_path)

    if payload["execute"] and payload["unauthorized_inputs"]:
        payload["validation_errors"].append("execute=true rejected due to unauthorized inputs")
        payload["validation_passed"] = False

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT_DIR / output_dir
    json_path = output_dir / "full_model_activation_plan.json"
    md_path = output_dir / "full_model_activation_plan.md"
    write_report(
        payload=payload,
        json_path=json_path,
        md_path=md_path,
        title="Full Model Activation Plan",
        bullets=[
            f"status: `{payload['status']}`",
            f"execute: `{payload['execute']}`",
            f"validation_passed: `{payload['validation_passed']}`",
            f"unauthorized_inputs_count: `{len(payload['unauthorized_inputs'])}`",
            f"training_export_authorized: `{payload['training_export_authorized']}`",
        ],
    )

    print(f"FULL_MODEL_ACTIVATION_PLAN_JSON={json_path.as_posix()}")
    print(f"FULL_MODEL_ACTIVATION_PLAN_MD={md_path.as_posix()}")
    print(f"PLAN_STATUS={payload['status']}")
    print(f"VALIDATION_PASSED={payload['validation_passed']}")
    print("AUDIO_PROCESSING_PERFORMED=False")
    print("SOURCE_SEPARATION_PERFORMED=False")
    print("TRANSCRIPTION_PERFORMED=False")
    print("EMBEDDINGS_GENERATED=False")
    print("SYMBOLIC_GENERATION_PERFORMED=False")
    print("TRAINING_PERFORMED=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
