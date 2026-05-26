from __future__ import annotations

import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT_DIR / "reports" / "composition_projects"
OUT_JSON = OUT_DIR / "drawing_board_composition_brief.json"
OUT_MD = OUT_DIR / "drawing_board_composition_brief.md"


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def build_brief() -> dict:
    dossier = _read_json(ROOT_DIR / "reports" / "source_taste_understanding" / "source_database_taste_dossier.json")
    principles_path = ROOT_DIR / "datasets" / "source_taste_understanding" / "source_database_generative_principles.jsonl"
    principles = []
    if principles_path.exists():
        for raw in principles_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                principles.append(row)
    return {
        "brief_id": "drawing_board_composition_brief_v1",
        "source_db_principles": [str(row.get("statement", "")) for row in principles[:5] if str(row.get("statement", "")).strip()],
        "rejected_principles": list(dossier.get("rejected_principles", [])),
        "witness_influence": list(dossier.get("witness_influence_summary", [])),
        "weak_evidence_areas": list(dossier.get("weak_evidence_limits", [])),
        "transformation_vs_copy": str(
            dossier.get("transformation_vs_copy_policy", "Generate transformed material and avoid direct copying.")
        ),
        "composition_objective": "Understanding-first composition sketch shaped by evidence-backed source principles.",
    }


def main() -> int:
    brief = build_brief()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(brief, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = [
        "# Drawing Board Composition Brief",
        "",
        f"- brief_id: `{brief['brief_id']}`",
        f"- transformation_vs_copy: {brief['transformation_vs_copy']}",
        "",
        "## Source DB Principles",
        *[f"- {row}" for row in brief["source_db_principles"]],
        "",
        "## Rejected Principles",
        *[f"- {row}" for row in brief["rejected_principles"]],
        "",
        "## Witness Influence",
        *[f"- {row}" for row in brief["witness_influence"]],
        "",
        "## Weak Evidence Areas",
        *[f"- {row}" for row in brief["weak_evidence_areas"]],
    ]
    OUT_MD.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"DRAWING_BOARD_BRIEF_JSON={OUT_JSON.as_posix()}")
    print(f"DRAWING_BOARD_BRIEF_MD={OUT_MD.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
