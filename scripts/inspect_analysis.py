from __future__ import annotations

import argparse
import json
from pathlib import Path


def inspect_analysis(analysis_path: Path) -> list[str]:
    payload = json.loads(analysis_path.read_text(encoding="utf-8"))
    diagnostics = payload.get("diagnostics", {}) if isinstance(payload, dict) else {}
    if not isinstance(diagnostics, dict):
        diagnostics = {}
    candidates = payload.get("boundary_candidates", []) if isinstance(payload, dict) else []
    if not isinstance(candidates, list):
        candidates = []
    source_features = sorted(
        {str(candidate.get("source_feature", "unknown")) for candidate in candidates if isinstance(candidate, dict)}
    )
    contributing = sorted(
        {
            tuple(candidate.get("contributing_features", []))
            for candidate in candidates
            if isinstance(candidate, dict) and isinstance(candidate.get("contributing_features"), list)
        }
    )
    lines = [
        f"analysis_path: {analysis_path.resolve().as_posix()}",
        f"analysis_backend: {payload.get('analysis_backend')}",
        f"analysis_version: {payload.get('analysis_version')}",
        f"analysis_run_id: {payload.get('analysis_run_id')}",
        f"candidate_density: {diagnostics.get('candidate_density')}",
        f"features_keys: {sorted(list((payload.get('features') or {}).keys()))}",
        f"boundary_candidates_length: {len(candidates)}",
        f"candidate_source_features: {source_features}",
        f"candidate_contributing_features: {contributing}",
        f"raw_peak_count_by_feature: {diagnostics.get('raw_peak_count_by_feature')}",
        f"fused_candidate_count: {diagnostics.get('fused_candidate_count')}",
        f"returned_candidate_count: {diagnostics.get('returned_candidate_count')}",
    ]
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect one structure_analysis.json file.")
    parser.add_argument("analysis_path", help="Path to structure_analysis.json")
    args = parser.parse_args()
    for line in inspect_analysis(Path(args.analysis_path)):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
