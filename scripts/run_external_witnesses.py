from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.external_analyzer_common import parse_provider_list, run_and_write_external_analyzers


def main() -> int:
    parser = argparse.ArgumentParser(description="Run external witness analyzers without failing on unavailable providers.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    parser.add_argument("providers", nargs="?", default="essentia,musicnn,beat_tracker,music21,omnizart")
    args = parser.parse_args()
    summary = run_and_write_external_analyzers(
        Path(args.performance_manifest),
        selected_providers=parse_provider_list(args.providers),
    )
    print(f"EXTERNAL_WITNESS_DIR={summary['external_output_dir']}")
    print("EXTERNAL_WITNESS_RESULTS=" + json.dumps(summary["results"], ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
