from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.composition_projects import (  # noqa: E402
    analyze_draft,
    build_composition_control_spec,
    build_drawing_board_composition_brief,
    compare_draft_to_database,
    load_context,
    write_draft_analysis_outputs,
    write_local_manifest,
)


def main() -> int:
    context = load_context()
    write_local_manifest(context)
    draft_dossier = analyze_draft(context)
    write_draft_analysis_outputs(draft_dossier)
    database_dossier = compare_draft_to_database(draft_dossier)
    spec = build_composition_control_spec(draft_dossier, database_dossier, context)
    brief = build_drawing_board_composition_brief(draft_dossier, database_dossier, spec)
    print(f"DRAWING_BOARD_BRIEF_STATUS={brief.get('status', 'unknown')}")
    print(f"DRAWING_BOARD_BRIEF_JSON={(ROOT_DIR / 'reports' / 'composition_projects' / 'drawing_board_composition_brief.json').as_posix()}")
    return 0 if brief.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
