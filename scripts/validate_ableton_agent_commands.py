from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.ableton_agent import AbletonCommand, validate_ableton_commands  # noqa: E402
from scripts.plan_ableton_agent_change import build_mock_project_state, build_sample_intent  # noqa: E402
from features.ableton_agent import build_ableton_change_plan  # noqa: E402


def _read_commands_from_plan(path: Path) -> list[AbletonCommand]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    commands: list[AbletonCommand] = []
    for row in payload.get("proposed_ableton_commands", []):
        commands.append(
            AbletonCommand(
                command_type=row["command_type"],
                parameters=row.get("parameters", {}),
                human_review_required=bool(row.get("human_review_required", True)),
                generated_candidate=bool(row.get("generated_candidate", False)),
                notes=str(row.get("notes", "")),
            )
        )
    return commands


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Ableton Agent scaffold commands.")
    parser.add_argument(
        "--plan-json",
        default="reports/ableton_agent/ableton_agent_change_plan.json",
        help="Optional existing plan JSON path. If missing, commands are built from sample intent/state.",
    )
    args = parser.parse_args()
    plan_path = Path(args.plan_json)
    if not plan_path.is_absolute():
        plan_path = ROOT_DIR / plan_path

    project_state = build_mock_project_state()
    if plan_path.exists():
        commands = _read_commands_from_plan(plan_path)
    else:
        plan = build_ableton_change_plan(build_sample_intent(), project_state)
        commands = plan.proposed_ableton_commands

    result = validate_ableton_commands(commands, project_state)
    print(f"COMMAND_VALIDATION_PASSED={result.valid}")
    print(f"VALID_COMMAND_COUNT={len(result.sanitized_commands)}")
    print(f"WARNING_COUNT={len(result.warnings)}")
    print(f"ERROR_COUNT={len(result.errors)}")
    print(f"HUMAN_REVIEW_REQUIRED={result.human_review_required}")
    if result.warnings:
        print("WARNINGS_BEGIN")
        for warning in result.warnings:
            print(f"- {warning}")
        print("WARNINGS_END")
    if result.errors:
        print("ERRORS_BEGIN")
        for error in result.errors:
            print(f"- {error}")
        print("ERRORS_END")
    return 0 if result.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
