from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT_DIR / "reports" / "privacy"
REPORT_JSON = REPORT_DIR / "privacy_leak_scan_report.json"
REPORT_MD = REPORT_DIR / "privacy_leak_scan_report.md"

FORBIDDEN_MARKERS = [
    "C:\\Users\\",
    "C:/Users/",
    "C:/" + "Users/" + "izzyo",
    "C:\\" + "Users\\" + "izzyo",
    r"OneDrive\Desktop\sounds",
    "OneDrive/Desktop/sounds",
    "private_synplant_seed_paths",
    "sample_seed_records.jsonl",
]

ENFORCED_PUBLIC_PATH_PREFIXES = [
    "outputs/generated_midi/",
    "outputs/model_backend_runs/",
    "outputs/symbolic_ensemble_v1/",
    "reports/",
]

ENFORCED_PUBLIC_SAMPLE_ID_PREFIXES = [
    "reports/synplant/",
    "reports/texture_intelligence/",
    "outputs/generated_midi/",
    "outputs/model_backend_runs/",
]

# These are private/local by design and should not be treated as public-leak targets.
ALLOWLIST_PATH_SNIPPETS = [
    "config/controlled_batches/",
    "outputs/ableton_project_v1/",
    "outputs/tangible_generation_v1/",
    "datasets/sample_libraries/",
    "reports/sample_libraries/",
    "reports/integration/privacy_debt_report.",
    "reports/taste_learning/feedback_ingestion_report.",
    "reports/privacy/",
    "scripts/check_privacy_leaks.py",
    "tests/",
]


@dataclass(frozen=True)
class LeakMatch:
    path: str
    marker: str
    debt_type: str
    line_count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "marker": self.marker,
            "debt_type": self.debt_type,
            "line_count": self.line_count,
        }


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, check=False, capture_output=True, text=True)


def _list_tracked_files(project_root: Path) -> list[Path]:
    result = _run_git(["git", "ls-files"], cwd=project_root)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git ls-files failed")
    files: list[Path] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        files.append(project_root / line)
    return files


def _list_changed_files(project_root: Path) -> set[str]:
    merge_base = _run_git(["git", "merge-base", "HEAD", "main"], cwd=project_root)
    if merge_base.returncode != 0:
        return set()
    base_hash = merge_base.stdout.strip()
    if not base_hash:
        return set()
    changed = _run_git(["git", "diff", "--name-only", f"{base_hash}...HEAD"], cwd=project_root)
    if changed.returncode != 0:
        return set()
    return {line.strip().replace("\\", "/") for line in changed.stdout.splitlines() if line.strip()}


def _is_text_file(path: Path) -> bool:
    try:
        data = path.read_bytes()
    except OSError:
        return False
    if b"\x00" in data:
        return False
    return True


def _is_allowlisted(relative_path: str) -> bool:
    lower = relative_path.lower()
    if lower.endswith(".local.json"):
        return True
    return any(snippet in lower for snippet in ALLOWLIST_PATH_SNIPPETS)


def _is_enforced_public_path(relative_path: str) -> bool:
    lower = relative_path.lower()
    return any(lower.startswith(prefix) for prefix in ENFORCED_PUBLIC_PATH_PREFIXES)


def _is_enforced_public_sample_surface(relative_path: str) -> bool:
    lower = relative_path.lower()
    return any(lower.startswith(prefix) for prefix in ENFORCED_PUBLIC_SAMPLE_ID_PREFIXES)


def _scan_file(path: Path, relative_path: str) -> list[tuple[str, int]]:
    if not _is_text_file(path):
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []

    matches: list[tuple[str, int]] = []
    for marker in FORBIDDEN_MARKERS:
        count = text.count(marker)
        if count > 0:
            matches.append((marker, count))
    # Enforce local sample identifiers only in public report/output surfaces.
    if _is_enforced_public_sample_surface(relative_path):
        for marker in ("local_sounds_desktop__", "!a secret"):
            count = text.count(marker)
            if count > 0:
                matches.append((marker, count))

    # If a real local config file is accidentally tracked, treat as leak.
    if relative_path.endswith("config/sample_libraries/local_sounds_library.json"):
        matches.append(("tracked_local_sounds_library_json", 1))
    # Seed suggestions containing private source path are not allowed in tracked/public outputs.
    if "seed_suggestions" in relative_path and ("C:/Users/" in text or "C:\\Users\\" in text):
        matches.append(("private_seed_suggestion_path", 1))
    # Public Synplant/texture reports should not expose direct per-sample filename/source_path fields.
    if relative_path.startswith("reports/synplant/") and ".public." in relative_path:
        if "\"source_path\"" in text:
            matches.append(("public_synplant_report_contains_source_path_field", text.count("\"source_path\"")))
        if "\"filename\"" in text:
            matches.append(("public_synplant_report_contains_filename_field", text.count("\"filename\"")))
        if "\"sample_id\"" in text:
            matches.append(("public_synplant_report_contains_sample_id_field", text.count("\"sample_id\"")))
    if relative_path == "reports/texture_intelligence/texture_analysis_plan.public.json":
        if "\"source_path\"" in text:
            matches.append(("public_texture_report_contains_source_path_field", text.count("\"source_path\"")))
        if "\"filename\"" in text:
            matches.append(("public_texture_report_contains_filename_field", text.count("\"filename\"")))
    return matches


def scan_privacy_leaks(
    project_root: Path = ROOT_DIR,
    tracked_files: list[Path] | None = None,
    changed_files: set[str] | None = None,
    strict_mode: bool = False,
) -> dict[str, Any]:
    tracked = tracked_files if tracked_files is not None else _list_tracked_files(project_root)
    changed = changed_files if changed_files is not None else _list_changed_files(project_root)

    new_public_leaks: list[LeakMatch] = []
    historical_debt: list[LeakMatch] = []
    skipped_private_or_allowlisted: list[str] = []

    for path in tracked:
        try:
            rel = path.resolve().relative_to(project_root.resolve()).as_posix()
        except Exception:  # noqa: BLE001
            continue
        if _is_allowlisted(rel):
            skipped_private_or_allowlisted.append(rel)
            continue
        found = _scan_file(path, rel)
        if not found:
            continue
        for marker, count in found:
            enforced_public = _is_enforced_public_path(rel)
            leak = LeakMatch(
                path=rel,
                marker=marker,
                debt_type=(
                    "new_or_changed_public_leak"
                    if rel in changed
                    else ("enforced_public_leak" if enforced_public else "pre_existing_historical_path_debt")
                ),
                line_count=count,
            )
            if rel in changed or enforced_public:
                new_public_leaks.append(leak)
            else:
                historical_debt.append(leak)

    status = "fail" if new_public_leaks else "ok"
    if strict_mode and historical_debt:
        status = "fail"
    payload = {
        "status": status,
        "strict_mode": strict_mode,
        "new_public_leak_count": len(new_public_leaks),
        "pre_existing_historical_path_debt_count": len(historical_debt),
        "new_public_leaks": [item.as_dict() for item in new_public_leaks],
        "pre_existing_historical_path_debt": [item.as_dict() for item in historical_debt],
        "skipped_private_or_allowlisted_paths": sorted(set(skipped_private_or_allowlisted)),
        "limitations": [
            "String-based scan only; semantic privacy issues may require manual review.",
            "Historical debt is reported but does not fail unless file is newly changed on this branch.",
        ],
    }
    return payload


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Privacy Leak Scan Report",
        "",
        f"- status: `{payload['status']}`",
        f"- strict_mode: `{payload['strict_mode']}`",
        f"- new_public_leak_count: `{payload['new_public_leak_count']}`",
        f"- pre_existing_historical_path_debt_count: `{payload['pre_existing_historical_path_debt_count']}`",
        "",
        "## New Public Leaks",
    ]
    if payload["new_public_leaks"]:
        for item in payload["new_public_leaks"]:
            lines.append(f"- `{item['path']}` marker=`{item['marker']}` count=`{item['line_count']}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Pre-existing Historical Path Debt"])
    if payload["pre_existing_historical_path_debt"]:
        for item in payload["pre_existing_historical_path_debt"][:50]:
            lines.append(f"- `{item['path']}` marker=`{item['marker']}` count=`{item['line_count']}`")
        remaining = len(payload["pre_existing_historical_path_debt"]) - 50
        if remaining > 0:
            lines.append(f"- ... and {remaining} more")
    else:
        lines.append("- none")

    lines.extend(["", "## Limitations"])
    lines.extend([f"- {item}" for item in payload["limitations"]])
    lines.append("")
    return "\n".join(lines)


def write_privacy_report(project_root: Path = ROOT_DIR, *, strict_mode: bool = False) -> tuple[Path, Path, dict[str, Any]]:
    payload = scan_privacy_leaks(project_root=project_root, strict_mode=strict_mode)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(payload), encoding="utf-8")
    return REPORT_JSON, REPORT_MD, payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan tracked files for privacy leak markers.")
    parser.add_argument("--strict", action="store_true", help="Fail when historical debt is detected.")
    args = parser.parse_args()
    json_path, md_path, payload = write_privacy_report(project_root=ROOT_DIR, strict_mode=args.strict)
    print(f"PRIVACY_LEAK_REPORT_JSON={json_path.as_posix()}")
    print(f"PRIVACY_LEAK_REPORT_MD={md_path.as_posix()}")
    print(f"PRIVACY_SCAN_STATUS={payload['status']}")
    print(f"NEW_PUBLIC_LEAK_COUNT={payload['new_public_leak_count']}")
    print(f"PRE_EXISTING_HISTORICAL_PATH_DEBT_COUNT={payload['pre_existing_historical_path_debt_count']}")
    return 1 if payload["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
