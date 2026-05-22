from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.build_model_consensus import build_model_consensus
from scripts.external_analyzer_common import external_output_dir, resolve_performance_context
from scripts.feature_dataset_common import save_json


def build_consensus(performance_manifest_path: Path) -> dict[str, Any]:
    ctx = resolve_performance_context(performance_manifest_path)
    payload = build_model_consensus(performance_manifest_path)
    payload["manual_review_recommendations"] = payload.get("recommended_review_items", [])
    payload["conflict_warnings"] = payload.get("unresolved_conflicts", [])
    payload["witness_not_truth_principle"] = "External model outputs are optional witnesses and never primary truth."
    save_json(external_output_dir(ctx["feature_dir"]) / "feature_consensus.json", payload)
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
