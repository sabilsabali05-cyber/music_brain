from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT_DIR / "reports" / "privacy"
PLAN_JSON = REPORT_DIR / "historical_path_scrub_plan.json"
PLAN_MD = REPORT_DIR / "historical_path_scrub_plan.md"

PATH_PATTERNS = [
    re.compile(r"[A-Za-z]:[/\\]Users[/\\][^\s\"']+"),
]
SAFE_APPLY_EXTENSIONS = {".md", ".txt", ".json"}
SKIP_PREFIXES = ("datasets/", "features/", "library/", "samples/")


def _run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT_DIR, check=False, capture_output=True, text=True)


def _tracked_files() -> list[Path]:
    result = _run_git(["git", "ls-files"])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git ls-files failed")
    files: list[Path] = []
    for line in result.stdout.splitlines():
        text = line.strip()
        if text:
            files.append(ROOT_DIR / text)
    return files


def build_historical_scrub_plan(*, apply_safe: bool = False) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    safe_apply_candidates: list[str] = []
    skipped_candidates: list[str] = []
    replacements_applied = 0

    for file_path in _tracked_files():
        rel = file_path.relative_to(ROOT_DIR).as_posix()
        if rel.startswith(".git/") or not file_path.exists():
            continue
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if not text:
            continue
        local_matches: list[str] = []
        for pattern in PATH_PATTERNS:
            local_matches.extend(pattern.findall(text))
        if not local_matches:
            continue

        findings.append(
            {
                "path": rel,
                "match_count": len(local_matches),
                "sample_match": local_matches[0],
            }
        )
        if rel.startswith(SKIP_PREFIXES):
            skipped_candidates.append(rel)
            continue
        if file_path.suffix.lower() in SAFE_APPLY_EXTENSIONS:
            safe_apply_candidates.append(rel)
            if apply_safe:
                updated = text
                for pattern in PATH_PATTERNS:
                    updated = pattern.sub("REDACTED_LOCAL_PATH", updated)
                if updated != text:
                    file_path.write_text(updated, encoding="utf-8")
                    replacements_applied += 1
        else:
            skipped_candidates.append(rel)

    status = "applied_safe_updates" if apply_safe else "dry_run_ready"
    payload = {
        "status": status,
        "finding_count": len(findings),
        "safe_apply_candidate_count": len(safe_apply_candidates),
        "skipped_candidate_count": len(skipped_candidates),
        "replacements_applied": replacements_applied,
        "safe_apply_candidates": safe_apply_candidates[:100],
        "skipped_candidates": skipped_candidates[:100],
        "findings": findings[:100],
        "provenance": {
            "planner": "scripts/plan_historical_path_scrub.py",
            "apply_safe": apply_safe,
            "audio_processing_performed": False,
        },
        "limitations": [
            "Pattern-based path detection only.",
            "Safe apply only touches non-dataset text/json/markdown files.",
        ],
    }
    return payload


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Historical Path Scrub Plan",
        "",
        f"- status: `{payload['status']}`",
        f"- finding_count: `{payload['finding_count']}`",
        f"- safe_apply_candidate_count: `{payload['safe_apply_candidate_count']}`",
        f"- replacements_applied: `{payload['replacements_applied']}`",
        "",
        "## Safe Apply Candidates",
    ]
    lines.extend([f"- `{item}`" for item in payload["safe_apply_candidates"]] or ["- none"])
    lines.extend(["", "## Skipped Candidates"])
    lines.extend([f"- `{item}`" for item in payload["skipped_candidates"]] or ["- none"])
    lines.extend(["", "## Limitations"])
    lines.extend([f"- {item}" for item in payload["limitations"]])
    lines.append("")
    return "\n".join(lines)


def write_historical_scrub_plan(*, apply_safe: bool = False) -> tuple[Path, Path, dict[str, Any]]:
    payload = build_historical_scrub_plan(apply_safe=apply_safe)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    PLAN_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    PLAN_MD.write_text(_render_markdown(payload), encoding="utf-8")
    return PLAN_JSON, PLAN_MD, payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Build historical local-path scrub plan.")
    parser.add_argument("--apply-safe", action="store_true", help="Apply replacements to safe candidate files.")
    args = parser.parse_args()
    json_path, md_path, payload = write_historical_scrub_plan(apply_safe=args.apply_safe)
    print(f"HISTORICAL_PATH_SCRUB_PLAN_JSON={json_path.as_posix()}")
    print(f"HISTORICAL_PATH_SCRUB_PLAN_MD={md_path.as_posix()}")
    print(f"HISTORICAL_PATH_SCRUB_STATUS={payload['status']}")
    print(f"HISTORICAL_PATH_FINDING_COUNT={payload['finding_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
