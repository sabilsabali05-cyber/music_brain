from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.cloud_execution.cloud_artifact_policy import redact_public_payload, redact_public_text
from scripts.cloud_full_activation_common import ACTIVATION_REPORTS_DIR, EXAMPLE_MANIFEST_PATH, now_iso, read_json


def build_plan_payload(manifest_path: Path) -> dict[str, object]:
    manifest = read_json(manifest_path)
    allow_export = bool(manifest.get("allow_ableton_export", False))
    evidence_exists = False
    status = "planned_only"
    if not evidence_exists:
        status = "planned_no_evidence"
    if allow_export and evidence_exists:
        status = "ready_for_manual_export_gate"
    return {
        "status": status,
        "created_at": now_iso(),
        "manifest_path": manifest_path.as_posix(),
        "allow_ableton_export": allow_export,
        "evidence_exists": evidence_exists,
        "export_performed": False,
        "next_step": "Generate evidence and explicitly set allow_ableton_export=true in local manifest before export.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan Ableton review export from activation report outputs.")
    parser.add_argument("--manifest", default=EXAMPLE_MANIFEST_PATH.as_posix())
    parser.add_argument("--output-dir", default=ACTIVATION_REPORTS_DIR.as_posix())
    args = parser.parse_args()
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = ROOT_DIR / manifest_path
    payload = build_plan_payload(manifest_path)
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT_DIR / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "ableton_review_export_plan.json"
    md_path = output_dir / "ableton_review_export_plan.md"
    json_path.write_text(json.dumps(redact_public_payload(payload), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = [
        "# Ableton Review Export Plan",
        "",
        f"- status: `{payload['status']}`",
        f"- allow_ableton_export: `{payload['allow_ableton_export']}`",
        f"- evidence_exists: `{payload['evidence_exists']}`",
        "- export_performed: `False`",
    ]
    md_path.write_text(redact_public_text("\n".join(lines) + "\n"), encoding="utf-8")
    print(f"ABLETON_REVIEW_EXPORT_PLAN_JSON={json_path.as_posix()}")
    print(f"ABLETON_REVIEW_EXPORT_PLAN_MD={md_path.as_posix()}")
    print(f"ABLETON_REVIEW_EXPORT_PLAN_STATUS={payload['status']}")
    print("ABLETON_EXPORT_PERFORMED=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
