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
    stage_allows_execution,
    unauthorized_inputs,
    validate_manifest,
    write_report,
)

MODEL_STAGE = {
    "demucs": "source_separation",
    "yourmt3": "transcription",
    "basic_pitch": "transcription",
    "muq": "embeddings",
    "mert": "embeddings",
    "essentia": "embeddings",
    "musicbert": "embeddings",
    "moonbeam": "symbolic_generation",
    "midigpt": "symbolic_generation",
    "text2midi": "symbolic_generation",
}


def _route_models(manifest: dict[str, Any], model_rows: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    execute = bool(manifest.get("execute", False))
    allow_flags = manifest.get("allow_flags", {})
    allow_flags = allow_flags if isinstance(allow_flags, dict) else {}
    model_cfg = normalized_model_config(manifest)
    routed: list[dict[str, Any]] = []

    for model_id, cfg in sorted(model_cfg.items()):
        requested = bool(cfg.get("enabled", False))
        available_row = model_rows.get(model_id, {})
        available = bool(available_row.get("available", False))
        unavailable_reason = str(available_row.get("reason", "not_in_checker"))
        stage = MODEL_STAGE.get(model_id, "unknown_stage")

        if not requested:
            routed.append(
                {
                    "model_id": model_id,
                    "stage": stage,
                    "status": "skipped_not_requested",
                    "reason": "manifest_model_disabled",
                }
            )
            continue

        if not execute:
            routed.append(
                {
                    "model_id": model_id,
                    "stage": stage,
                    "status": "skipped_dry_run",
                    "reason": "execute=false",
                }
            )
            continue

        if not bool(allow_flags.get("allow_audio_processing", False)):
            routed.append(
                {
                    "model_id": model_id,
                    "stage": stage,
                    "status": "blocked_missing_allow_audio_processing",
                    "reason": "allow_flags.allow_audio_processing=false",
                }
            )
            continue

        if not stage_allows_execution(stage, allow_flags):
            routed.append(
                {
                    "model_id": model_id,
                    "stage": stage,
                    "status": "blocked_missing_stage_allow_flag",
                    "reason": f"allow flag for stage `{stage}` is false",
                }
            )
            continue

        if not available:
            routed.append(
                {
                    "model_id": model_id,
                    "stage": stage,
                    "status": "skipped_unavailable",
                    "reason": unavailable_reason,
                }
            )
            continue

        routed.append(
            {
                "model_id": model_id,
                "stage": stage,
                "status": "execution_not_implemented_scaffold_only",
                "reason": "scaffold routes model but does not execute processing",
            }
        )
    return routed


def build_run_report(manifest: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    validation = validate_manifest(manifest)
    unauthorized = unauthorized_inputs(manifest)
    execute = bool(manifest.get("execute", False))
    rejected_execute = execute and bool(unauthorized)
    model_rows = model_rows_from_checker()
    model_routing = _route_models(manifest, model_rows)

    return {
        "status": "dry_run" if not execute else ("rejected_unauthorized_inputs" if rejected_execute else "gated_execute_scaffold"),
        "created_at": now_iso(),
        "manifest_path": manifest_path.as_posix(),
        "execute_requested": execute,
        "execute_allowed": execute and not rejected_execute and validation.valid,
        "validation_passed": validation.valid and not rejected_execute,
        "validation_errors": validation.errors
        + (["execute=true rejected due to unauthorized inputs"] if rejected_execute else []),
        "validation_warnings": validation.warnings,
        "unauthorized_inputs": unauthorized,
        "model_routing": model_routing,
        "audio_input_processing_blocked": not (execute and validation.valid and not rejected_execute),
        "provenance_outputs": [],
        "model_outputs_exist": False,
        "no_silent_fallback": True,
        "modal_called": False,
        "weights_downloaded": False,
        **REQUIRED_DRY_RUN_FLAGS,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full model activation scaffold with strict safety gates.")
    parser.add_argument("manifest", help="Path to activation manifest JSON.")
    parser.add_argument("--output-dir", default=REPORTS_DIR.as_posix())
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = ROOT_DIR / manifest_path
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload = build_run_report(manifest, manifest_path)

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT_DIR / output_dir
    json_path = output_dir / "full_model_activation_run_report.json"
    md_path = output_dir / "full_model_activation_run_report.md"
    write_report(
        payload=payload,
        json_path=json_path,
        md_path=md_path,
        title="Full Model Activation Run Report",
        bullets=[
            f"status: `{payload['status']}`",
            f"execute_requested: `{payload['execute_requested']}`",
            f"execute_allowed: `{payload['execute_allowed']}`",
            f"validation_passed: `{payload['validation_passed']}`",
            f"unauthorized_inputs_count: `{len(payload['unauthorized_inputs'])}`",
        ],
    )

    print(f"FULL_MODEL_ACTIVATION_RUN_JSON={json_path.as_posix()}")
    print(f"FULL_MODEL_ACTIVATION_RUN_MD={md_path.as_posix()}")
    print(f"RUN_STATUS={payload['status']}")
    print(f"EXECUTE_ALLOWED={payload['execute_allowed']}")
    print("AUDIO_PROCESSING_PERFORMED=False")
    print("SOURCE_SEPARATION_PERFORMED=False")
    print("TRANSCRIPTION_PERFORMED=False")
    print("EMBEDDINGS_GENERATED=False")
    print("SYMBOLIC_GENERATION_PERFORMED=False")
    print("TRAINING_PERFORMED=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
