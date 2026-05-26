from __future__ import annotations

import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT_DIR / "outputs" / "essence_composition_v1"
OUT_JSON = OUT_DIR / "essence_composition_brief.json"
OUT_MD = OUT_DIR / "essence_composition_brief.md"


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def main() -> int:
    drawing_board = _read_json(ROOT_DIR / "reports" / "composition_projects" / "drawing_board_composition_brief.json")
    essence = {
        "composition_id": "essence_composition_v1",
        "status": "planned",
        "source_db_principles_cited": drawing_board.get("source_db_principles", []),
        "rejected_principles": drawing_board.get("rejected_principles", []),
        "witness_influence": drawing_board.get("witness_influence", []),
        "weak_evidence_areas": drawing_board.get("weak_evidence_areas", []),
        "transformation_vs_copy": drawing_board.get("transformation_vs_copy", ""),
        "notes": [
            "This stage produces a brief only; no direct source copying and no score-first optimization.",
            "When evidence is weak, constraints are softened and marked for critique.",
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(essence, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = [
        "# Essence Composition Brief",
        "",
        f"- composition_id: `{essence['composition_id']}`",
        f"- status: `{essence['status']}`",
        f"- transformation_vs_copy: {essence['transformation_vs_copy']}",
        "",
        "## Source DB Principles Cited",
        *[f"- {row}" for row in essence["source_db_principles_cited"]],
        "",
        "## Rejected Principles",
        *[f"- {row}" for row in essence["rejected_principles"]],
        "",
        "## Witness Influence",
        *[f"- {row}" for row in essence["witness_influence"]],
        "",
        "## Weak Evidence Areas",
        *[f"- {row}" for row in essence["weak_evidence_areas"]],
    ]
    OUT_MD.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"ESSENCE_COMPOSITION_BRIEF_JSON={OUT_JSON.as_posix()}")
    print(f"ESSENCE_COMPOSITION_BRIEF_MD={OUT_MD.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
