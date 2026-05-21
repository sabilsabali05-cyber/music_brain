from __future__ import annotations

import argparse
import json
from pathlib import Path


def diagnose_boundaries(manifest_path: Path) -> list[dict[str, object]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    diagnostics = manifest.get("segmentation_diagnostics", {})
    if not isinstance(diagnostics, dict):
        diagnostics = {}
    rows = diagnostics.get("candidate_evaluations", [])
    if not isinstance(rows, list):
        rows = []
    normalized: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        evidence = row.get("feature_evidence", {})
        if not isinstance(evidence, dict):
            evidence = {}
        normalized.append(
            {
                "time_seconds": row.get("time_seconds"),
                "confidence": row.get("tuned_confidence", row.get("confidence")),
                "accepted": bool(row.get("accepted")),
                "rejection_reason": row.get("rejection_reason", "unknown"),
                "energy_change": evidence.get("energy_change", 0.0),
                "onset_change": evidence.get("onset_change", 0.0),
                "chroma_change": evidence.get("chroma_change", 0.0),
                "timbre_change": evidence.get("timbre_change", 0.0),
                "combined_novelty": evidence.get("combined_novelty", 0.0),
                "nearest_segment_distance": row.get("nearest_segment_distance"),
                "boundary_reason": row.get("boundary_reason"),
            }
        )
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose boundary candidate acceptance/rejection.")
    parser.add_argument("manifest_path", help="Path to segments_manifest.json")
    args = parser.parse_args()
    rows = diagnose_boundaries(Path(args.manifest_path))
    if not rows:
        print("No boundary candidate diagnostics available.")
        return 0
    header = [
        "time_seconds",
        "confidence",
        "accepted",
        "rejection_reason",
        "energy_change",
        "onset_change",
        "chroma_change",
        "timbre_change",
        "combined_novelty",
        "nearest_segment_distance",
        "boundary_reason",
    ]
    print("\t".join(header))
    for row in rows:
        print("\t".join(str(row.get(col, "")) for col in header))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
