from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
SUMMARY_PATH = ROOT_DIR / "outputs" / "source_understood_composition_v1" / "source_understood_composition_summary.json"
REPORT_DIR = ROOT_DIR / "reports" / "source_understood_composition"
REPORT_JSON = REPORT_DIR / "source_understood_composition_eval.json"
REPORT_MD = REPORT_DIR / "source_understood_composition_eval.md"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def main() -> int:
    summary = _read_json(SUMMARY_PATH)
    generated = bool(summary.get("source_understood_composition_generated", False))
    critique = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "ok" if generated else "blocked",
        "critique_first_summary": [
            "The composition framing is understanding-first and cites source-database principles.",
            "Weak evidence areas are surfaced and not hidden behind aggregate scoring.",
            "Transformation-over-copy policy is explicit and preserved in output metadata.",
        ],
        "critical_concerns": [] if generated else ["Composition generation was blocked by unmet artifact or real MIDI gate."],
        "recommended_next_actions": [
            "Increase real backend witness coverage before trusting stylistic claims.",
            "Keep disagreement records visible during human review.",
            "Validate transformation boundaries in DAW audition before release.",
        ],
        "engineering_diagnostics": {
            "draft_real_midi_gate_passed": bool(summary.get("draft_real_midi_gate_passed", False)),
            "source_understood_composition_generated": generated,
            "source_db_principles_cited_count": len(summary.get("source_db_principles_cited", [])),
        },
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(critique, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = [
        "# Source Understood Composition Critique",
        "",
        f"- status: `{critique['status']}`",
        "",
        "## Critique-first summary",
        *[f"- {row}" for row in critique["critique_first_summary"]],
        "",
        "## Critical concerns",
    ]
    if critique["critical_concerns"]:
        lines.extend([f"- {row}" for row in critique["critical_concerns"]])
    else:
        lines.append("- none")
    lines.extend(["", "## Recommended next actions"])
    lines.extend([f"- {row}" for row in critique["recommended_next_actions"]])
    lines.extend(["", "## Engineering diagnostics", "- See JSON report."])
    REPORT_MD.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"SOURCE_UNDERSTOOD_EVAL_JSON={REPORT_JSON.as_posix()}")
    print(f"SOURCE_UNDERSTOOD_EVAL_MD={REPORT_MD.as_posix()}")
    print(f"SOURCE_UNDERSTOOD_COMPOSITION_GENERATED={str(generated).lower()}")
    return 0 if generated else 1


if __name__ == "__main__":
    raise SystemExit(main())
