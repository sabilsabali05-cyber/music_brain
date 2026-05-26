from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.composition_projects import (
    analyze_draft,
    build_composition_control_spec,
    compare_draft_to_database,
    generate_candidates,
    load_context,
    write_draft_analysis_outputs,
    write_local_manifest,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate presentable composition candidates.")
    parser.add_argument("--config", default="", help="Optional local config override path.")
    args = parser.parse_args()
    context = load_context(Path(args.config) if args.config else None)
    write_local_manifest(context)
    analysis = analyze_draft(context)
    write_draft_analysis_outputs(analysis)
    comparison = compare_draft_to_database(analysis)
    spec = build_composition_control_spec(analysis, comparison, context)
    report = generate_candidates(spec, context)
    print(f"CANDIDATES_GENERATED={report.get('candidates_generated', 0)}")
    print(f"CANDIDATE_ROOT={(ROOT_DIR / 'outputs' / 'presentable_composition_from_draft_v1' / 'candidates').as_posix()}")
    return 0 if not analysis.missing_local_midi_draft else 1


if __name__ == "__main__":
    raise SystemExit(main())
