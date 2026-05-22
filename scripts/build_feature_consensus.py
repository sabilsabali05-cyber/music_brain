from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.external_analyzer_common import external_output_dir, resolve_performance_context
from scripts.feature_dataset_common import load_json, save_json


def _safe_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = load_json(path)
    except Exception:  # noqa: BLE001
        return {}
    return payload


def build_consensus(performance_manifest_path: Path) -> dict[str, Any]:
    ctx = resolve_performance_context(performance_manifest_path)
    output_dir = external_output_dir(ctx["feature_dir"])
    comparison = _safe_json(output_dir / "external_feature_comparison.json")
    essentia = _safe_json(output_dir / "essentia_features.json")
    musicnn = _safe_json(output_dir / "musicnn_features.json")

    agreements = comparison.get("agreements", []) if isinstance(comparison.get("agreements"), list) else []
    disagreements = comparison.get("disagreements", []) if isinstance(comparison.get("disagreements"), list) else []
    confidence_boosts: list[str] = []
    conflict_warnings: list[str] = []
    manual_review: list[str] = []

    if agreements:
        confidence_boosts.append("External witnesses agree with internal signals in one or more domains.")
    if disagreements:
        conflict_warnings.append("External witnesses disagree with internal signals; verify by listening and score review.")
        manual_review.append("Review tempo/key disagreements before exporting downstream labels.")
    if essentia.get("status") in {"unavailable", "failed"}:
        manual_review.append("Essentia unavailable/failed; install dependencies if high-confidence rhythm/key witness is needed.")
    if musicnn.get("status") in {"unavailable", "failed"}:
        manual_review.append("musicnn unavailable/failed; install dependencies if tag witness coverage is required.")
    if not agreements and not disagreements:
        manual_review.append("No external comparison evidence was found; consensus remains internal-only.")

    payload = {
        "performance_id": ctx["performance_id"],
        "segment_run_id": ctx["segment_run_id"],
        "agreements": agreements,
        "disagreements": disagreements,
        "confidence_boosts": confidence_boosts,
        "conflict_warnings": conflict_warnings,
        "provider_limitations": {
            "essentia": essentia.get("limitations", []),
            "musicnn": musicnn.get("limitations", []),
        },
        "manual_review_recommendations": sorted(set(manual_review)),
        "witness_not_truth_principle": "External model outputs are optional witnesses and never primary truth.",
    }
    save_json(output_dir / "feature_consensus.json", payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a consensus summary from internal and external feature signals.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    args = parser.parse_args()
    payload = build_consensus(Path(args.performance_manifest))
    print("FEATURE_CONSENSUS_JSON=" + json.dumps(payload, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
