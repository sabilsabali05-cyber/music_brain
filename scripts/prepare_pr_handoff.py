from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Dict, List


REPORTS_DIR = Path("reports/agent_handoffs")
JSON_PATH = REPORTS_DIR / "latest_handoff.json"
MD_PATH = REPORTS_DIR / "latest_handoff.md"
OUTPUT_PATH = REPORTS_DIR / "pr_handoff_body.md"


def _list_block(items: List[str]) -> str:
    if not items:
        return "- (none)"
    return "\n".join(f"- {item}" for item in items)


def _metrics_block(metrics: Dict[str, str]) -> str:
    if not metrics:
        return "- (none)"
    return "\n".join(f"- {key}: {value}" if value else f"- {key}" for key, value in metrics.items())


def _parse_simple_markdown(markdown_text: str) -> Dict[str, object]:
    parsed: Dict[str, object] = {
        "phase": "unspecified-phase",
        "goal": "No goal supplied.",
        "tests_result": [],
        "validation_results": [],
        "generated_artifacts": [],
        "metrics_before": {},
        "metrics_after": {},
        "risks_concerns": [],
        "open_user_decisions": [],
        "constraints_followed": [],
        "recommended_next_step": "Await audit feedback before next major phase.",
    }

    phase_match = re.search(r"^- phase:\s*(.+)$", markdown_text, re.MULTILINE)
    goal_match = re.search(r"^- goal:\s*(.+)$", markdown_text, re.MULTILINE)
    if phase_match:
        parsed["phase"] = phase_match.group(1).strip()
    if goal_match:
        parsed["goal"] = goal_match.group(1).strip()
    return parsed


def load_handoff() -> Dict[str, object]:
    if JSON_PATH.exists():
        return json.loads(JSON_PATH.read_text(encoding="utf-8"))
    if MD_PATH.exists():
        return _parse_simple_markdown(MD_PATH.read_text(encoding="utf-8"))
    raise FileNotFoundError(
        f"Expected {JSON_PATH} or {MD_PATH}. Run scripts/write_agent_handoff.py first."
    )


def build_pr_body(payload: Dict[str, object]) -> str:
    summary_lines = [
        f"Phase: {payload.get('phase', 'unspecified-phase')}",
        f"Goal: {payload.get('goal', 'No goal supplied.')}",
    ]

    lines = [
        "## summary",
        _list_block(summary_lines),
        "",
        "## test results",
        _list_block(payload.get("tests_result", [])),
        "",
        "## validation results",
        _list_block(payload.get("validation_results", [])),
        "",
        "## artifact paths",
        _list_block(payload.get("generated_artifacts", [])),
        "",
        "## metrics before/after",
        "**before**",
        _metrics_block(payload.get("metrics_before", {})),
        "",
        "**after**",
        _metrics_block(payload.get("metrics_after", {})),
        "",
        "## risks",
        _list_block(payload.get("risks_concerns", [])),
        "",
        "## questions for Sabil",
        _list_block(payload.get("open_user_decisions", [])),
        "",
        "## audit checklist for ChatGPT",
        "- Confirm implementation diff matches stated goal.",
        "- Confirm tests and validators are sufficient and passing.",
        "- Confirm all constraints were respected.",
        "- Identify remaining risks and edge cases.",
        "- Recommend the exact next prompt for Cursor.",
        "",
        "@ChatGPT audit request:",
        "- verify diff matches goal",
        "- verify tests/validators",
        "- verify constraints",
        "- identify risk",
        "- recommend next prompt",
        "",
        f"_Source handoff:_ `{JSON_PATH}`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    try:
        payload = load_handoff()
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    pr_body = build_pr_body(payload)
    OUTPUT_PATH.write_text(pr_body, encoding="utf-8")
    sys.stdout.write(pr_body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
