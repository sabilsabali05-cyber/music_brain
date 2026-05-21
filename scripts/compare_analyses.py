from __future__ import annotations

import argparse
import json
from pathlib import Path


def summarize_analysis(analysis_path: Path) -> dict[str, object]:
    payload = json.loads(analysis_path.read_text(encoding="utf-8"))
    diagnostics = payload.get("diagnostics", {}) if isinstance(payload, dict) else {}
    if not isinstance(diagnostics, dict):
        diagnostics = {}
    candidates = payload.get("boundary_candidates", []) if isinstance(payload, dict) else []
    if not isinstance(candidates, list):
        candidates = []
    top = sorted(
        [row for row in candidates if isinstance(row, dict)],
        key=lambda row: float(row.get("confidence", 0.0) or 0.0),
        reverse=True,
    )[:5]
    top_summary = ",".join(
        f"{float(row.get('time_seconds', 0.0) or 0.0):.3f}@{float(row.get('confidence', 0.0) or 0.0):.3f}:{row.get('source_feature', '-')}"
        for row in top
    )
    run_id = str(payload.get("analysis_run_id", analysis_path.parent.name))
    available = diagnostics.get("available_features", [])
    missing = diagnostics.get("missing_features", [])
    return {
        "run_id": run_id,
        "backend": payload.get("analysis_backend"),
        "density": diagnostics.get("candidate_density"),
        "analysis_version": payload.get("analysis_version"),
        "available_features": ",".join(available) if isinstance(available, list) else available,
        "missing_features": ",".join(missing) if isinstance(missing, list) else missing,
        "boundary_candidate_count": len(candidates),
        "raw_peak_count_by_feature": diagnostics.get("raw_peak_count_by_feature"),
        "fused_candidate_count": diagnostics.get("fused_candidate_count"),
        "returned_candidate_count": diagnostics.get("returned_candidate_count"),
        "top_candidates": top_summary,
        "analysis_path": analysis_path.resolve().as_posix(),
    }


def compare_analyses(source_folder: Path) -> list[dict[str, object]]:
    manifests: list[Path] = []
    root_analysis = source_folder / "structure_analysis.json"
    if root_analysis.exists():
        manifests.append(root_analysis)
    for child in sorted(source_folder.iterdir()):
        if not child.is_dir():
            continue
        analysis_path = child / "structure_analysis.json"
        if analysis_path.exists():
            manifests.append(analysis_path)
    return [summarize_analysis(path) for path in manifests]


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare analysis runs for one source analysis folder.")
    parser.add_argument("source_folder", help="Path to samples/analysis/<safe_source_name>/")
    args = parser.parse_args()
    rows = compare_analyses(Path(args.source_folder))
    if not rows:
        print("No analysis runs found.")
        return 0
    header = [
        "run_id",
        "backend",
        "density",
        "analysis_version",
        "available_features",
        "missing_features",
        "boundary_candidate_count",
        "raw_peak_count_by_feature",
        "fused_candidate_count",
        "returned_candidate_count",
        "top_candidates",
        "analysis_path",
    ]
    print("\t".join(header))
    for row in rows:
        print("\t".join(str(row.get(col, "")) for col in header))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
