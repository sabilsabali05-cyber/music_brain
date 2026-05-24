from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.ableton_agent import evaluate_review_policy, validate_ableton_commands  # noqa: E402
from scripts.plan_ableton_agent_change import (  # noqa: E402
    build_change_plan_payload,
    build_mock_project_state,
)

REPORT_DIR = ROOT_DIR / "reports" / "ableton_agent"
DRY_RUN_JSON = "ableton_agent_dry_run_report.json"
DRY_RUN_MD = "ableton_agent_dry_run_report.md"


def build_dry_run_payload() -> dict[str, Any]:
    plan_payload = build_change_plan_payload()
    project_state = build_mock_project_state()
    commands = plan_payload["proposed_ableton_commands"]
    # Rehydrate command rows through validator expectations.
    from features.ableton_agent import AbletonCommand

    command_objects = [
        AbletonCommand(
            command_type=row["command_type"],
            parameters=row.get("parameters", {}),
            human_review_required=bool(row.get("human_review_required", True)),
            generated_candidate=bool(row.get("generated_candidate", False)),
            notes=str(row.get("notes", "")),
        )
        for row in commands
    ]
    validation = validate_ableton_commands(command_objects, project_state)
    review = evaluate_review_policy(
        risk_warnings=plan_payload["risk_warnings"] + validation.warnings,
        validation_errors=validation.errors,
        commands_executed=False,
    )
    return {
        "status": "dry_run_completed" if validation.valid else "dry_run_failed_validation",
        "ableton_connected": False,
        "live_set_modified": False,
        "commands_generated": len(validation.sanitized_commands) > 0,
        "commands_executed": False,
        "human_review_required": True,
        "model_generation_performed": False,
        "audio_processing_performed": False,
        "training_performed": False,
        "no_gui_automation": True,
        "real_live_set_writes_future_gated": True,
        "interpreted_musical_intent": plan_payload["interpreted_musical_intent"],
        "proposed_arrangement_changes": plan_payload["proposed_arrangement_changes"],
        "proposed_generated_candidates_needed": plan_payload["proposed_generated_candidates_needed"],
        "proposed_ableton_commands": validation.sanitized_commands,
        "risk_warnings": plan_payload["risk_warnings"] + validation.warnings,
        "human_review_checklist": review.checklist,
        "validation_warnings": validation.warnings,
        "validation_errors": validation.errors,
        "review_blockers": review.blockers,
        "no_real_ableton_operations": True,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Ableton Agent Dry Run Report",
        "",
        f"- status: `{payload['status']}`",
        f"- ableton_connected: `{payload['ableton_connected']}`",
        f"- live_set_modified: `{payload['live_set_modified']}`",
        f"- commands_generated: `{payload['commands_generated']}`",
        f"- commands_executed: `{payload['commands_executed']}`",
        f"- human_review_required: `{payload['human_review_required']}`",
        f"- model_generation_performed: `{payload['model_generation_performed']}`",
        f"- audio_processing_performed: `{payload['audio_processing_performed']}`",
        f"- training_performed: `{payload['training_performed']}`",
        "",
        "## Human Review Checklist",
    ]
    lines.extend([f"- {item}" for item in payload["human_review_checklist"]])
    lines.extend(["", "## Proposed Ableton Commands"])
    lines.extend([f"- `{item['command_type']}` generated_candidate=`{item['generated_candidate']}`" for item in payload["proposed_ableton_commands"]])
    lines.extend(["", "## Risk Warnings"])
    lines.extend([f"- {item}" for item in payload["risk_warnings"]])
    lines.append("")
    return "\n".join(lines)


def write_dry_run_report(output_dir: Path) -> tuple[Path, Path, dict[str, Any]]:
    payload = build_dry_run_payload()
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / DRY_RUN_JSON
    md_path = output_dir / DRY_RUN_MD
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(payload), encoding="utf-8")
    return json_path, md_path, payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Ableton Agent Bridge dry-run (no real Ableton operations).")
    parser.add_argument("--output-dir", default=REPORT_DIR.as_posix())
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT_DIR / output_dir
    json_path, md_path, payload = write_dry_run_report(output_dir)
    print(f"ABLETON_AGENT_DRY_RUN_JSON={json_path.as_posix()}")
    print(f"ABLETON_AGENT_DRY_RUN_MD={md_path.as_posix()}")
    print(f"ABLETON_CONNECTED={payload['ableton_connected']}")
    print(f"LIVE_SET_MODIFIED={payload['live_set_modified']}")
    print(f"COMMANDS_GENERATED={payload['commands_generated']}")
    print(f"COMMANDS_EXECUTED={payload['commands_executed']}")
    print(f"HUMAN_REVIEW_REQUIRED={payload['human_review_required']}")
    print("MODEL_GENERATION_PERFORMED=False")
    print("AUDIO_PROCESSING_PERFORMED=False")
    print("TRAINING_PERFORMED=False")
    return 0 if not payload["validation_errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
