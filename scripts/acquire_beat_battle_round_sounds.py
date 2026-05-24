from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.beat_battle_site_automation.round_detector import read_snapshot  # noqa: E402
from features.beat_battle_site_automation.sound_acquisition import acquire_round_sounds  # noqa: E402
from features.beat_battle_site_automation.site_config_schema import load_optional_local_site_config  # noqa: E402


def main() -> int:
    config, blocker = load_optional_local_site_config(ROOT_DIR)
    report_root = ROOT_DIR / "reports" / "beat_battle_site_automation"
    report_json = report_root / "sound_acquisition_report.json"
    report_md = report_root / "sound_acquisition_report.md"
    report_root.mkdir(parents=True, exist_ok=True)
    if config is None:
        payload = {"sounds_acquired": False, "acquired_count": 0, "blocker": blocker}
        report_json.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        report_md.write_text("# Sound Acquisition Report\n\n- sounds_acquired: `false`\n- blocker: `missing_local_site_config`\n", encoding="utf-8")
        print(f"SOUND_ACQUISITION_REPORT_JSON={report_json.as_posix()}")
        return 1
    snapshot = read_snapshot((ROOT_DIR / config.session.manual_round_snapshot_path).resolve())
    round_id = str(snapshot.get("active_round_id", "")).strip()
    sound_urls = [str(x) for x in snapshot.get("active_round_sound_urls", []) if str(x).strip()]
    if not round_id:
        payload = {"sounds_acquired": False, "acquired_count": 0, "blocker": "active_round_missing_id"}
        report_json.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        report_md.write_text("# Sound Acquisition Report\n\n- sounds_acquired: `false`\n- blocker: `active_round_missing_id`\n", encoding="utf-8")
        print(f"SOUND_ACQUISITION_REPORT_JSON={report_json.as_posix()}")
        return 1
    result = acquire_round_sounds(config=config, project_root=ROOT_DIR, round_id=round_id, round_sound_urls=sound_urls)
    payload = {
        "round_id": result.round_id,
        "sounds_acquired": result.sounds_acquired,
        "acquired_count": result.acquired_count,
        "manifest_path": result.manifest_path,
        "raw_audio_folder": result.raw_audio_folder,
        "strategy_summary": result.strategy_summary,
        "blocker": result.blocker,
    }
    report_json.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    report_md.write_text(
        "\n".join(
            [
                "# Sound Acquisition Report",
                "",
                f"- round_id: `{result.round_id}`",
                f"- sounds_acquired: `{str(result.sounds_acquired).lower()}`",
                f"- acquired_count: `{result.acquired_count}`",
                f"- manifest_path: `{result.manifest_path}`",
                f"- blocker: `{result.blocker or 'none'}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"SOUND_ACQUISITION_REPORT_JSON={report_json.as_posix()}")
    print(f"ROUND_MANIFEST={result.manifest_path}")
    return 0 if result.sounds_acquired else 1


if __name__ == "__main__":
    raise SystemExit(main())
