from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.beat_battle_site_automation.browser_session import as_dict, setup_browser_session  # noqa: E402
from features.beat_battle_site_automation.site_config_schema import load_optional_local_site_config  # noqa: E402


def main() -> int:
    config, blocker = load_optional_local_site_config(ROOT_DIR)
    report_path = ROOT_DIR / "reports" / "beat_battle_site_automation" / "browser_session_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if config is None:
        payload = {"ok": False, "manual_action_required": True, "blocker": blocker}
        report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        print(f"BROWSER_SESSION_REPORT={report_path.as_posix()}")
        print(f"BLOCKER={blocker}")
        return 1
    result = setup_browser_session(config, ROOT_DIR)
    payload = as_dict(result)
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"BROWSER_SESSION_REPORT={report_path.as_posix()}")
    print(f"BLOCKER={result.blocker or 'none'}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
