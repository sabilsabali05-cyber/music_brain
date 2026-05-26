from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.composition_projects import (
    analyze_draft,
    compare_draft_to_database,
    load_context,
    write_draft_analysis_outputs,
    write_local_manifest,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build database musical understanding dossier from draft understanding."
    )
    parser.add_argument("--config", default="", help="Optional local config override path.")
    args = parser.parse_args()
    context = load_context(Path(args.config) if args.config else None)
    write_local_manifest(context)
    analysis = analyze_draft(context)
    write_draft_analysis_outputs(analysis)
    report = compare_draft_to_database(analysis)
    print(f"DATABASE_UNDERSTANDING_CONFIDENCE={report.get('confidence', 0.0)}")
    print(f"DATABASE_UNDERSTANDING_STATUS={report.get('status', 'unknown')}")
    return 0 if not analysis.missing_local_midi_draft else 1


if __name__ == "__main__":
    raise SystemExit(main())
