from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.source_loop_extraction import extract_source_loops

CONTROLLED_BATCH_PATH = ROOT_DIR / "datasets" / "source_audio_study" / "source_audio_controlled_batch.jsonl"
LOCAL_PATH_MAP_PATH = ROOT_DIR / "local_source_audio_study" / "source_audio_path_map.local.json"
MODEL_WITNESS_AUDIT_PATH = ROOT_DIR / "reports" / "model_witnesses" / "model_witness_audit.json"
SOURCE_TASTE_DOSSIER_PATH = ROOT_DIR / "reports" / "source_taste_understanding" / "source_database_taste_dossier.json"
AUTHORIZATION_CONFIG_PATH = ROOT_DIR / "config" / "source_audio_study_authorization.local.json"

LOCAL_EXTRACT_ROOT = ROOT_DIR / "local_source_audio_study" / "extracted_loops_v1"

OUT_DIR = ROOT_DIR / "datasets" / "source_loop_extraction"
OUT_JSONL = OUT_DIR / "extracted_source_loops.jsonl"
REPORT_DIR = ROOT_DIR / "reports" / "source_loop_extraction"
REPORT_MD = REPORT_DIR / "source_loop_extraction_report.md"
REPORT_JSON = REPORT_DIR / "source_loop_extraction_report.json"


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Source Loop Extraction Report",
        "",
        f"- generated_at: `{datetime.now(UTC).isoformat()}`",
        f"- considered_controlled_batch_rows: `{report.get('considered_controlled_batch_rows', 0)}`",
        f"- extracted_clip_rows: `{report.get('extracted_clip_rows', 0)}`",
        f"- actual_source_audio_snippets_extracted: `{report.get('actual_source_audio_snippets_extracted', 0)}`",
        f"- eligible_for_buddy_generation_count: `{report.get('eligible_for_buddy_generation_count', 0)}`",
        f"- missing_local_path_count: `{report.get('missing_local_path_count', 0)}`",
        f"- missing_audio_file_count: `{report.get('missing_audio_file_count', 0)}`",
        f"- extraction_failures_count: `{report.get('extraction_failures_count', 0)}`",
        "",
        "## Witness Availability Snapshot",
    ]
    available = report.get("witnesses_available", [])
    unavailable = report.get("witnesses_unavailable", [])
    if isinstance(available, list) and available:
        lines.append("- available: `" + ", ".join(str(x) for x in available) + "`")
    else:
        lines.append("- available: `none`")
    if isinstance(unavailable, list) and unavailable:
        lines.append("- unavailable: `" + ", ".join(str(x) for x in unavailable) + "`")
    else:
        lines.append("- unavailable: `none`")
    lines.extend(["", "## Policy"])
    policy = report.get("policy", {})
    if isinstance(policy, dict):
        for key, value in policy.items():
            lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Hard Gate", f"- {report.get('hard_gate', 'n/a')}", "", "## Limitations"])
    for item in report.get("limitations", []):
        lines.append(f"- {item}")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    rows, report = extract_source_loops(
        controlled_batch_path=CONTROLLED_BATCH_PATH,
        local_path_map_path=LOCAL_PATH_MAP_PATH,
        model_witness_audit_path=MODEL_WITNESS_AUDIT_PATH,
        source_taste_dossier_path=SOURCE_TASTE_DOSSIER_PATH,
        authorization_config_path=AUTHORIZATION_CONFIG_PATH,
        local_extract_root=LOCAL_EXTRACT_ROOT,
        emit_preview_mp3=False,
    )
    _write_jsonl(OUT_JSONL, rows)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(report), encoding="utf-8")

    print(f"EXTRACTED_SOURCE_LOOPS_JSONL={OUT_JSONL.as_posix()}")
    print(f"SOURCE_LOOP_EXTRACTION_REPORT_MD={REPORT_MD.as_posix()}")
    print(f"SOURCE_LOOP_EXTRACTION_REPORT_JSON={REPORT_JSON.as_posix()}")
    print(f"LOCAL_EXTRACTED_LOOP_FOLDER={LOCAL_EXTRACT_ROOT.as_posix()}")
    print(f"ACTUAL_SOURCE_AUDIO_SNIPPETS_EXTRACTED={report.get('actual_source_audio_snippets_extracted', 0)}")
    print(f"ELIGIBLE_FOR_BUDDY_GENERATION_COUNT={report.get('eligible_for_buddy_generation_count', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
