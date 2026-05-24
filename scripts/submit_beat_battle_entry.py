from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.beat_battle_site_automation.site_config_schema import load_optional_local_site_config  # noqa: E402
from features.beat_battle_site_automation.submission_uploader import as_dict, submit_entry  # noqa: E402


def _latest_render() -> Path | None:
    renders = sorted((ROOT_DIR / "renders" / "beat_battle_site").glob("*/submission.wav"))
    return renders[-1] if renders else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit Beat Battle entry.")
    parser.add_argument("--manual-submit-confirmed", action="store_true", help="Confirm manual pre-submit check completed.")
    args = parser.parse_args()
    config, blocker = load_optional_local_site_config(ROOT_DIR)
    report_root = ROOT_DIR / "reports" / "beat_battle_site_automation"
    report_json = report_root / "submission_report.json"
    report_md = report_root / "submission_report.md"
    report_root.mkdir(parents=True, exist_ok=True)
    if config is None:
        payload = {
            "upload_success": False,
            "submitted": False,
            "stopped_pre_submit": True,
            "status": "blocked_missing_local_site_config",
            "blocker": blocker,
            "allow_auto_submit": False,
            "require_manual_submit_confirmation": True,
        }
        report_json.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        report_md.write_text("# Submission Report\n\n- status: `blocked_missing_local_site_config`\n", encoding="utf-8")
        return 1
    render_path = _latest_render() or Path("missing.wav")
    result = submit_entry(config=config, render_path=render_path, manual_submit_confirmed=args.manual_submit_confirmed)
    payload = as_dict(result)
    report_json.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    report_md.write_text(
        "\n".join(
            [
                "# Submission Report",
                "",
                f"- status: `{result.status}`",
                f"- upload_success: `{str(result.upload_success).lower()}`",
                f"- submitted: `{str(result.submitted).lower()}`",
                f"- stopped_pre_submit: `{str(result.stopped_pre_submit).lower()}`",
                f"- blocker: `{result.blocker or 'none'}`",
                f"- allow_auto_submit: `{str(result.allow_auto_submit).lower()}`",
                f"- require_manual_submit_confirmation: `{str(result.require_manual_submit_confirmation).lower()}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"SUBMISSION_REPORT_JSON={report_json.as_posix()}")
    print(f"SUBMISSION_STATUS={result.status}")
    return 0 if result.submitted else 1


if __name__ == "__main__":
    raise SystemExit(main())
