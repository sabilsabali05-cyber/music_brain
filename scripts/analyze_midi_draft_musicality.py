from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.composition_projects import (
    FALLBACK_FIXTURE_USED_STATUS,
    INPUT_PATH_REQUIRED_STATUS,
    MISSING_LOCAL_MIDI_CONFIG_STATUS,
    OK_STATUS,
    analyze_draft,
    load_context,
    write_draft_analysis_outputs,
    write_local_manifest,
)

REAL_PATH_REDACTION = "<PRIVATE_LOCAL_PATH>"


def _run_git(args: list[str]) -> str:
    proc = subprocess.run(["git", *args], cwd=ROOT_DIR, capture_output=True, text=True, check=False)
    return (proc.stdout or proc.stderr or "").strip()


def _scan_fixture_introductions() -> list[str]:
    matches: list[str] = []
    for rel in ("scripts", "features", "tests"):
        base = ROOT_DIR / rel
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if "validation_inputs/draft.mid" in text or "validation_inputs\\draft.mid" in text:
                matches.append(path.relative_to(ROOT_DIR).as_posix())
    return sorted(matches)


def _redact_path(raw: str) -> str:
    return raw.replace("\\", "/").replace("C:/Users/", f"{REAL_PATH_REDACTION}/")


def _build_audit(
    *,
    context,
    expected_real_path: str,
    command_used: str,
) -> dict[str, object]:
    fixture_hits = _scan_fixture_introductions()
    manifest_hits = []
    for rel in ("scripts", "tests"):
        base = ROOT_DIR / rel
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if "local_input_manifest.json" in text and "write_local_manifest" not in text:
                manifest_hits.append(path.relative_to(ROOT_DIR).as_posix())
    expected_real = Path(expected_real_path).resolve() if expected_real_path else None
    resolved_real = context.local_input_midi_path.resolve() if context.local_input_midi_path else None
    return {
        "current_branch": _run_git(["rev-parse", "--abbrev-ref", "HEAD"]),
        "current_working_tree_status": _run_git(["status", "--short", "--branch"]),
        "config_file_read": context.config_path.as_posix(),
        "local_config_exists": context.config_exists,
        "resolved_input_midi_path": context.resolved_input_midi_path_redacted,
        "resolved_path_equals_real_user_path": bool(expected_real and resolved_real and resolved_real == expected_real),
        "fallback_fixture_used": context.fallback_fixture_used,
        "fixture_introduced_in": fixture_hits,
        "tests_or_scripts_overwrite_local_manifest": len(manifest_hits) > 0,
        "command_that_produced_jaca_draft_musical_understanding_md": command_used,
    }


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _write_md(path: Path, title: str, rows: dict[str, object]) -> None:
    lines = [f"# {title}", ""]
    for key, value in rows.items():
        lines.append(f"- {key}: `{json.dumps(value, ensure_ascii=True) if isinstance(value, (dict, list)) else value}`")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze local MIDI draft understanding (legacy musicality command compatibility)."
    )
    parser.add_argument("--config", default="", help="Optional local config override path.")
    parser.add_argument("--expected-real-midi-path", default="", help="Optional real MIDI path for equality audit.")
    parser.add_argument(
        "--command-used",
        default="scripts\\dev.cmd analyze-midi-draft-musicality",
        help="Exact command string for audit trace.",
    )
    args = parser.parse_args()
    prior_payload: dict[str, object] = {}
    prior_json = ROOT_DIR / "reports" / "composition_projects" / "jaca_draft_musical_understanding.json"
    if not prior_json.exists():
        prior_json = ROOT_DIR / "reports" / "composition_projects" / "jaca_draft_musicality_analysis.json"
    if prior_json.exists():
        try:
            loaded = json.loads(prior_json.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                prior_payload = loaded
        except json.JSONDecodeError:
            prior_payload = {}
    context = load_context(Path(args.config) if args.config else None, require_local_config=True, allow_fixture_for_tests=False)
    manifest = write_local_manifest(context)
    analysis = analyze_draft(context)
    outputs = write_draft_analysis_outputs(analysis)
    audit_payload = _build_audit(context=context, expected_real_path=args.expected_real_midi_path, command_used=args.command_used)
    audit_json = ROOT_DIR / "reports" / "composition_projects" / "real_draft_input_resolution_audit.json"
    audit_md = ROOT_DIR / "reports" / "composition_projects" / "real_draft_input_resolution_audit.md"
    _write_json(audit_json, audit_payload)
    _write_md(audit_md, "Real Draft Input Resolution Audit", audit_payload)

    current_payload = json.loads(outputs["json"].read_text(encoding="utf-8"))
    previous_source = str(prior_payload.get("source_path_redacted", prior_payload.get("resolved_input_midi_path_redacted", "unknown")))
    current_source = str(current_payload.get("resolved_input_midi_path_redacted", current_payload.get("source_path_redacted", "unknown")))
    previous_note_count = int(prior_payload.get("note_count", 0) or 0)
    current_note_count = int(current_payload.get("note_count", 0) or 0)
    previous_fixture_based = "validation_inputs/draft.mid" in previous_source.lower() or bool(
        prior_payload.get("fallback_fixture_used", False)
    )
    gate = {
        "real_midi_used": context.resolution_status == OK_STATUS and not context.fallback_fixture_used,
        "fallback_fixture_used": context.fallback_fixture_used,
        "note_count_gt_zero": current_note_count > 0,
    }
    gate["draft_understanding_usable"] = bool(
        gate["real_midi_used"] and gate["note_count_gt_zero"] and context.resolution_status == OK_STATUS
    )
    gate["generation_allowed"] = bool(gate["draft_understanding_usable"] and not gate["fallback_fixture_used"])

    comparison_payload: dict[str, object] = {
        "previous_dossier_source_path_redacted": previous_source,
        "current_dossier_source_path_redacted": current_source,
        "previous_note_count": previous_note_count,
        "current_note_count": current_note_count,
        "previous_duration_seconds": float(prior_payload.get("duration_seconds", 0.0) or 0.0),
        "current_duration_seconds": float(current_payload.get("duration_seconds", 0.0) or 0.0),
        "previous_fallback_fixture_used": bool(prior_payload.get("fallback_fixture_used", False)),
        "current_fallback_fixture_used": bool(current_payload.get("fallback_fixture_used", False)),
        "previous_dossier_fixture_based": previous_fixture_based,
        "now_usable_for_generation_gate": gate["draft_understanding_usable"],
        "gate_status": gate,
    }
    compare_json = ROOT_DIR / "reports" / "composition_projects" / "fixture_vs_real_draft_understanding.json"
    compare_md = ROOT_DIR / "reports" / "composition_projects" / "fixture_vs_real_draft_understanding.md"
    _write_json(compare_json, comparison_payload)
    _write_md(compare_md, "Fixture vs Real Draft Understanding", comparison_payload)

    print(f"UNDERSTANDING_STATUS={context.resolution_status}")
    print(f"GATE_REAL_MIDI_USED={str(gate['real_midi_used']).lower()}")
    print(f"GATE_FALLBACK_FIXTURE_USED={str(gate['fallback_fixture_used']).lower()}")
    print(f"GATE_NOTE_COUNT_GT_ZERO={str(gate['note_count_gt_zero']).lower()}")
    print(f"GATE_DRAFT_UNDERSTANDING_USABLE={str(gate['draft_understanding_usable']).lower()}")
    print(f"GATE_GENERATION_ALLOWED={str(gate['generation_allowed']).lower()}")
    print(f"LOCAL_MANIFEST={manifest.as_posix()}")
    print(f"DRAFT_UNDERSTANDING_DOSSIER_JSON={outputs['json'].as_posix()}")
    print(f"DRAFT_UNDERSTANDING_DOSSIER_MD={outputs['md'].as_posix()}")
    print(f"MISSING_LOCAL_MIDI_DRAFT={str(analysis.missing_local_midi_draft).lower()}")
    if context.resolution_status in {MISSING_LOCAL_MIDI_CONFIG_STATUS, INPUT_PATH_REQUIRED_STATUS, FALLBACK_FIXTURE_USED_STATUS}:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
