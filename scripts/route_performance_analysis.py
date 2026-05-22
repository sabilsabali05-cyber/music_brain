from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.apply_analysis_routing import apply_analysis_routing
from scripts.classify_audio_asset import classify_audio_asset
from scripts.classify_content_regions import classify_content_regions
from scripts.evaluate_label_upgrade_candidates import evaluate_label_upgrade_candidates


def route_performance_analysis(performance_manifest_path: Path) -> dict[str, str]:
    asset = classify_audio_asset(performance_manifest_path)
    regions = classify_content_regions(performance_manifest_path)
    decisions = apply_analysis_routing(performance_manifest_path)
    upgrades = evaluate_label_upgrade_candidates(performance_manifest_path)
    return {
        "asset_classification_path": asset.as_posix(),
        "content_region_routes_path": regions.as_posix(),
        "analysis_routing_decisions_path": decisions.as_posix(),
        "label_upgrade_candidates_path": upgrades.as_posix(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full routing + weak-label upgrade scaffold for one performance.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    args = parser.parse_args()
    outputs = route_performance_analysis(Path(args.performance_manifest))
    for key, value in outputs.items():
        print(f"{key.upper()}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
