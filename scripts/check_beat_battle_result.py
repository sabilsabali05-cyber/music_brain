from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.beat_battle_site_automation.result_scraper import as_dict, ingest_result  # noqa: E402
from features.beat_battle_site_automation.site_config_schema import load_optional_local_site_config  # noqa: E402


def main() -> int:
    config, blocker = load_optional_local_site_config(ROOT_DIR)
    report_root = ROOT_DIR / "reports" / "beat_battle_site_automation"
    report_json = report_root / "result_report.json"
    report_md = report_root / "result_report.md"
    report_root.mkdir(parents=True, exist_ok=True)
    if config is None:
        payload = {"result_available": False, "feedback_ingested": False, "blocker": blocker}
        report_json.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        report_md.write_text("# Result Report\n\n- result_available: `false`\n- blocker: `missing_local_site_config`\n", encoding="utf-8")
        return 1
    result = ingest_result(config, ROOT_DIR)
    payload = as_dict(result)
    report_json.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    report_md.write_text(
        "\n".join(
            [
                "# Result Report",
                "",
                f"- result_available: `{str(result.result_available).lower()}`",
                f"- feedback_ingested: `{str(result.feedback_ingested).lower()}`",
                f"- blocker: `{result.blocker or 'none'}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"RESULT_REPORT_JSON={report_json.as_posix()}")
    print(f"RESULT_AVAILABLE={str(result.result_available).lower()}")
    return 0 if result.result_available else 1


if __name__ == "__main__":
    raise SystemExit(main())
