from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.beat_battle_site.kit_analysis import analyze_round_manifest  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze Beat Battle round kit.")
    parser.add_argument("--manifest", required=False, default="", help="Path to round_manifest.json")
    args = parser.parse_args()
    manifest = Path(args.manifest) if args.manifest else ROOT_DIR / "datasets" / "beat_battle_site" / "rounds"
    if manifest.is_dir():
        manifests = sorted(manifest.glob("*/round_manifest.json"))
        if not manifests:
            print("BLOCKER=missing_round_manifest")
            return 1
        manifest = manifests[-1]
    result = analyze_round_manifest(manifest)
    report_root = ROOT_DIR / "reports" / "beat_battle_site_automation"
    report_json = report_root / "kit_analysis_report.json"
    report_md = report_root / "kit_analysis_report.md"
    report_root.mkdir(parents=True, exist_ok=True)
    payload = {
        "round_id": result.round_id,
        "sounds_count": result.sounds_count,
        "analysis_mode": result.analysis_mode,
        "inferred_tags": result.inferred_tags,
        "sound_summaries": result.sound_summaries,
    }
    report_json.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    report_md.write_text(
        "\n".join(
            [
                "# Kit Analysis Report",
                "",
                f"- round_id: `{result.round_id}`",
                f"- sounds_count: `{result.sounds_count}`",
                f"- analysis_mode: `{result.analysis_mode}`",
                f"- inferred_tags: `{', '.join(result.inferred_tags) if result.inferred_tags else 'none'}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"KIT_ANALYSIS_REPORT_JSON={report_json.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
