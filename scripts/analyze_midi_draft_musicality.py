from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.composition_projects import analyze_draft, load_context, write_draft_analysis_outputs, write_local_manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze local MIDI draft understanding (legacy musicality command compatibility)."
    )
    parser.add_argument("--config", default="", help="Optional local config override path.")
    args = parser.parse_args()
    context = load_context(Path(args.config) if args.config else None)
    manifest = write_local_manifest(context)
    analysis = analyze_draft(context)
    outputs = write_draft_analysis_outputs(analysis)
    print(f"LOCAL_MANIFEST={manifest.as_posix()}")
    print(f"DRAFT_UNDERSTANDING_DOSSIER_JSON={outputs['json'].as_posix()}")
    print(f"DRAFT_UNDERSTANDING_DOSSIER_MD={outputs['md'].as_posix()}")
    print(f"MISSING_LOCAL_MIDI_DRAFT={str(analysis.missing_local_midi_draft).lower()}")
    return 0 if not analysis.missing_local_midi_draft else 1


if __name__ == "__main__":
    raise SystemExit(main())
