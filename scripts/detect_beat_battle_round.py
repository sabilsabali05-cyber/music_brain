from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.beat_battle_site_automation.round_detector import detect_active_round, read_snapshot  # noqa: E402
from features.beat_battle_site_automation.site_config_schema import load_optional_local_site_config  # noqa: E402


def main() -> int:
    config, blocker = load_optional_local_site_config(ROOT_DIR)
    report_root = ROOT_DIR / "reports" / "beat_battle_site_automation"
    report_json = report_root / "round_detection_report.json"
    report_md = report_root / "round_detection_report.md"
    report_root.mkdir(parents=True, exist_ok=True)
    if config is None:
        payload = {"active_round_detected": False, "round_id": "", "blocker": blocker}
        report_json.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        report_md.write_text(
            "# Round Detection Report\n\n- active_round_detected: `false`\n- blocker: `missing_local_site_config`\n",
            encoding="utf-8",
        )
        print(f"ROUND_DETECTION_REPORT_JSON={report_json.as_posix()}")
        return 1
    snapshot = read_snapshot((ROOT_DIR / config.session.manual_round_snapshot_path).resolve())
    result = detect_active_round(config, snapshot)
    payload = {
        "active_round_detected": result.active_round_detected,
        "round_id": result.round_id,
        "sound_urls": result.sound_urls,
        "diagnostics": result.diagnostics,
        "blocker": result.blocker,
    }
    report_json.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    report_md.write_text(
        "\n".join(
            [
                "# Round Detection Report",
                "",
                f"- active_round_detected: `{str(result.active_round_detected).lower()}`",
                f"- round_id: `{result.round_id or 'none'}`",
                f"- sound_urls_count: `{len(result.sound_urls)}`",
                f"- blocker: `{result.blocker or 'none'}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"ROUND_DETECTION_REPORT_JSON={report_json.as_posix()}")
    print(f"ACTIVE_ROUND_DETECTED={str(result.active_round_detected).lower()}")
    print(f"ROUND_ID={result.round_id or 'none'}")
    return 0 if result.active_round_detected else 1


if __name__ == "__main__":
    raise SystemExit(main())
