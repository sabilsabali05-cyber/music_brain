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
    parser = argparse.ArgumentParser(description="Run optional external analyzers for one performance.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    parser.add_argument("--providers", default="essentia,musicnn", help="Comma-separated providers")
    args = parser.parse_args()
    summary = run_and_write_external_analyzers(
        Path(args.performance_manifest),
        selected_providers=parse_provider_list(args.providers),
    )
    print(f"EXTERNAL_OUTPUT_DIR={summary['external_output_dir']}")
    print("EXTERNAL_RESULTS_JSON=" + json.dumps(summary["results"], ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
