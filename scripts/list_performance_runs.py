from __future__ import annotations

import argparse
from pathlib import Path

try:
    from scripts.performance_runs import ensure_run_tracking_fields, load_json, summarize_runs
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from performance_runs import ensure_run_tracking_fields, load_json, summarize_runs  # type: ignore


def list_performance_runs(performance_manifest_path: Path) -> dict[str, object]:
    manifest = load_json(performance_manifest_path)
    ensure_run_tracking_fields(manifest)
    return summarize_runs(manifest)


def main() -> int:
    parser = argparse.ArgumentParser(description="List active and historical runs for a performance manifest.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    args = parser.parse_args()

    summary = list_performance_runs(Path(args.performance_manifest))
    print(f"performance_id: {summary.get('performance_id')}")
    print(f"active_analysis_path: {summary.get('active_analysis_path')}")
    print(f"active_segments_manifest_path: {summary.get('active_segments_manifest_path')}")
    print(f"active_merged_midi_path: {summary.get('active_merged_midi_path')}")
    print("runs:")
    runs = summary.get("runs", [])
    if isinstance(runs, list):
        for run in runs:
            if not isinstance(run, dict):
                continue
            print(
                "  - "
                f"run_id={run.get('run_id')} "
                f"status={run.get('status')} "
                f"source_reason={run.get('source_reason')} "
                f"successful_windows={run.get('successful_windows')} "
                f"failed_windows={run.get('failed_windows')} "
                f"remaining_windows={run.get('remaining_windows')}"
            )
            print(f"    analysis_path={run.get('analysis_path')}")
            print(f"    segments_manifest_path={run.get('segments_manifest_path')}")
            print(f"    merged_midi_path={run.get('merged_midi_path')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
