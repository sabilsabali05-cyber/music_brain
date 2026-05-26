from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.composition_projects import (
    analyze_draft,
    build_composition_control_spec,
    compare_draft_to_database,
    load_context,
    write_draft_analysis_outputs,
    write_local_manifest,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build composition control spec.")
    parser.add_argument("--config", default="", help="Optional local config override path.")
    args = parser.parse_args()
    context = load_context(Path(args.config) if args.config else None)
    write_local_manifest(context)
    analysis = analyze_draft(context)
    write_draft_analysis_outputs(analysis)
    comparison = compare_draft_to_database(analysis)
    spec = build_composition_control_spec(analysis, comparison, context)
    print(f"COMPOSITION_SPEC_STATUS={spec.get('status', 'unknown')}")
    print(f"COMPOSITION_SPEC_PATH={(ROOT_DIR / 'outputs' / 'presentable_composition_from_draft_v1' / 'composition_control_spec.json').as_posix()}")
    print(f"COMPOSITION_SPEC_KEY_HINT={json.dumps(spec['control_targets']['key_hint'])}")
    return 0 if not analysis.missing_local_midi_draft else 1


if __name__ == "__main__":
    raise SystemExit(main())
