from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.beat_battle_site_automation.submission_renderer import as_dict, render_submission  # noqa: E402
from features.beat_battle_site_automation.site_config_schema import load_optional_local_site_config  # noqa: E402


def _latest_selected_draft() -> tuple[str, Path] | tuple[None, None]:
    root = ROOT_DIR / "outputs" / "beat_battle_site"
    candidates = sorted(root.glob("*/selected_draft/selected_draft.json"))
    if not candidates:
        return None, None
    path = candidates[-1]
    return path.parent.parent.name, path


def main() -> int:
    config, blocker = load_optional_local_site_config(ROOT_DIR)
    report_root = ROOT_DIR / "reports" / "beat_battle_site_automation"
    report_json = report_root / "submission_render_report.json"
    report_md = report_root / "submission_render_report.md"
    report_root.mkdir(parents=True, exist_ok=True)
    if config is None:
        payload = {"rendered_submission_available": False, "blocker": blocker}
        report_json.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        report_md.write_text("# Submission Render Report\n\n- rendered_submission_available: `false`\n- blocker: `missing_local_site_config`\n", encoding="utf-8")
        return 1
    round_id, selected = _latest_selected_draft()
    if round_id is None or selected is None:
        payload = {"rendered_submission_available": False, "blocker": "missing_selected_draft"}
        report_json.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        report_md.write_text("# Submission Render Report\n\n- rendered_submission_available: `false`\n- blocker: `missing_selected_draft`\n", encoding="utf-8")
        return 1
    result = render_submission(config=config, project_root=ROOT_DIR, round_id=round_id, selected_draft_path=selected)
    payload = as_dict(result)
    report_json.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    report_md.write_text(
        "\n".join(
            [
                "# Submission Render Report",
                "",
                f"- rendered_submission_available: `{str(result.rendered_submission_available).lower()}`",
                f"- round_id: `{result.round_id}`",
                f"- render_target_wav: `<LOCAL_RENDER_PATH>`",
                f"- render_target_mp3: `<LOCAL_RENDER_PATH>`",
                f"- blocker: `{result.blocker or 'none'}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"SUBMISSION_RENDER_REPORT_JSON={report_json.as_posix()}")
    print(f"RENDERED_SUBMISSION_AVAILABLE={str(result.rendered_submission_available).lower()}")
    return 0 if result.rendered_submission_available else 1


if __name__ == "__main__":
    raise SystemExit(main())
