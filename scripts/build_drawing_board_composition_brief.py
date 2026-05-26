from __future__ import annotations

import json
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


def build_brief() -> dict:
    context = load_context()
    write_local_manifest(context)
    draft_dossier = analyze_draft(context)
    write_draft_analysis_outputs(draft_dossier)
    database_dossier = compare_draft_to_database(draft_dossier)
    spec = build_composition_control_spec(draft_dossier, database_dossier, context)
    brief = build_drawing_board_composition_brief(draft_dossier, database_dossier, spec)
    principles_path = ROOT_DIR / "datasets" / "source_taste_understanding" / "source_database_generative_principles.jsonl"
    source_db_principles: list[str] = []
    if principles_path.exists():
        with principles_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                text = line.strip()
                if not text:
                    continue
                try:
                    row = json.loads(text)
                except json.JSONDecodeError:
                    continue
                if not isinstance(row, dict):
                    continue
                statement = str(row.get("statement", "")).strip()
                if statement:
                    source_db_principles.append(statement)
    brief["source_db_principles"] = source_db_principles
    output_json = ROOT_DIR / "reports" / "composition_projects" / "drawing_board_composition_brief.json"
    if output_json.exists():
        output_json.write_text(json.dumps(brief, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return brief


def main() -> int:
    brief = build_brief()
    print(f"DRAWING_BOARD_BRIEF_STATUS={brief.get('status', 'unknown')}")
    print(f"DRAWING_BOARD_BRIEF_JSON={(ROOT_DIR / 'reports' / 'composition_projects' / 'drawing_board_composition_brief.json').as_posix()}")
    return 0 if brief.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
