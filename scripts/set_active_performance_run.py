from __future__ import annotations

import argparse
from pathlib import Path

try:
    from scripts.performance_runs import ensure_run_tracking_fields, load_json, save_json, set_active_run
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from performance_runs import ensure_run_tracking_fields, load_json, save_json, set_active_run  # type: ignore


def set_active_performance_run(performance_manifest_path: Path, segments_manifest_path: Path) -> dict[str, object]:
    manifest = load_json(performance_manifest_path)
    ensure_run_tracking_fields(manifest)
    set_active_run(
        manifest,
        segments_manifest_path=segments_manifest_path.as_posix(),
        source_reason="manual_attach",
    )
    save_json(performance_manifest_path, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Set the canonical active run for a performance manifest.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    parser.add_argument("segments_manifest_path", help="Path to segments_manifest.json to mark active")
    args = parser.parse_args()

    performance_manifest_path = Path(args.performance_manifest)
    segments_manifest_path = Path(args.segments_manifest_path)
    if not segments_manifest_path.exists():
        raise FileNotFoundError(f"Segments manifest missing: {segments_manifest_path}")

    manifest = set_active_performance_run(performance_manifest_path, segments_manifest_path)
    print(f"ACTIVE_ANALYSIS_PATH={manifest.get('active_analysis_path')}")
    print(f"ACTIVE_SEGMENTS_MANIFEST_PATH={manifest.get('active_segments_manifest_path')}")
    print(f"ACTIVE_MERGED_MIDI_PATH={manifest.get('active_merged_midi_path')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
