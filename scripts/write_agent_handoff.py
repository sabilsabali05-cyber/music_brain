from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple


REPORTS_DIR = Path("reports/agent_handoffs")
JSON_PATH = REPORTS_DIR / "latest_handoff.json"
MD_PATH = REPORTS_DIR / "latest_handoff.md"

DEFAULT_CONSTRAINTS = [
    "No audio processing performed",
    "Modal not called",
    "No transcription executed",
    "No dependency installation",
    "No model training",
    "YourMT3 logic unchanged",
]


def _run_git_command(args: List[str]) -> Tuple[bool, str]:
    try:
        completed = subprocess.run(
            ["git", *args],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return False, f"git unavailable: {exc}"

    output = (completed.stdout or "") + (completed.stderr or "")
    output = output.strip()
    if completed.returncode != 0:
        return False, output or f"git {' '.join(args)} failed with code {completed.returncode}"
    return True, output


def _parse_metrics(entries: List[str]) -> Dict[str, str]:
    metrics: Dict[str, str] = {}
    for entry in entries:
        if "=" in entry:
            key, value = entry.split("=", 1)
            metrics[key.strip()] = value.strip()
        else:
            metrics[entry.strip()] = ""
    return metrics


def _collect_files_changed() -> List[str]:
    ok, output = _run_git_command(["status", "--porcelain"])
    if not ok:
        return []
    files: List[str] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        if len(line) >= 3 and line[2] == " ":
            path = line[3:]
        else:
            path = line[2:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        files.append(path.strip())
    return files


def build_markdown(payload: Dict[str, object]) -> str:
    def list_block(items: List[str]) -> str:
        if not items:
            return "- (none)"
        return "\n".join(f"- {item}" for item in items)

    def dict_block(values: Dict[str, str]) -> str:
        if not values:
            return "- (none)"
        return "\n".join(f"- {k}: {v}" if v else f"- {k}" for k, v in values.items())

    return (
        "# Latest Agent Handoff\n\n"
        f"- phase: {payload['phase']}\n"
        f"- goal: {payload['goal']}\n"
        f"- commit_hash: {payload['commit_hash']}\n\n"
        "## Constraints Followed\n"
        f"{list_block(payload['constraints_followed'])}\n\n"
        "## Files Changed\n"
        f"{list_block(payload['files_changed'])}\n\n"
        "## Commands Run\n"
        f"{list_block(payload['commands_run'])}\n\n"
        "## Test Results\n"
        f"{list_block(payload['tests_result'])}\n\n"
        "## Validation Results\n"
        f"{list_block(payload['validation_results'])}\n\n"
        "## Generated Artifacts\n"
        f"{list_block(payload['generated_artifacts'])}\n\n"
        "## Metrics Before\n"
        f"{dict_block(payload['metrics_before'])}\n\n"
        "## Metrics After\n"
        f"{dict_block(payload['metrics_after'])}\n\n"
        "## Risks / Concerns\n"
        f"{list_block(payload['risks_concerns'])}\n\n"
        "## Open User Decisions\n"
        f"{list_block(payload['open_user_decisions'])}\n\n"
        "## Recommended Next Step\n"
        f"- {payload['recommended_next_step']}\n\n"
        "## Git Status\n"
        "```text\n"
        f"{payload['git_status']}\n"
        "```\n"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write structured agent handoff reports.")
    parser.add_argument("--phase", default="unspecified-phase")
    parser.add_argument("--goal", default="No goal supplied.")
    parser.add_argument("--constraint", action="append", default=[])
    parser.add_argument("--command", action="append", default=[])
    parser.add_argument("--test", action="append", default=[])
    parser.add_argument("--validation", action="append", default=[])
    parser.add_argument("--artifact", action="append", default=[])
    parser.add_argument("--metric-before", action="append", default=[])
    parser.add_argument("--metric-after", action="append", default=[])
    parser.add_argument("--risk", action="append", default=[])
    parser.add_argument("--decision", action="append", default=[])
    parser.add_argument("--recommended-step", default="Await audit feedback before next major phase.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    files_changed = _collect_files_changed()

    head_ok, head_output = _run_git_command(["rev-parse", "HEAD"])
    commit_hash = head_output if head_ok else f"unavailable ({head_output})"

    status_ok, status_output = _run_git_command(["status", "-sb"])
    git_status = status_output if status_ok else f"unavailable ({status_output})"

    constraints_followed = args.constraint or list(DEFAULT_CONSTRAINTS)
    payload: Dict[str, object] = {
        "phase": args.phase,
        "goal": args.goal,
        "constraints_followed": constraints_followed,
        "files_changed": files_changed,
        "commands_run": args.command,
        "tests_result": args.test,
        "validation_results": args.validation,
        "generated_artifacts": args.artifact,
        "metrics_before": _parse_metrics(args.metric_before),
        "metrics_after": _parse_metrics(args.metric_after),
        "risks_concerns": args.risk,
        "open_user_decisions": args.decision,
        "recommended_next_step": args.recommended_step,
        "commit_hash": commit_hash,
        "git_status": git_status,
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    MD_PATH.write_text(build_markdown(payload), encoding="utf-8")

    print(f"Wrote handoff JSON: {JSON_PATH}")
    print(f"Wrote handoff Markdown: {MD_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
