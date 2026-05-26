from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.composition_projects import run_full_pipeline


def _load_source_understanding_context(root: Path) -> dict:
    dossier_path = root / "reports" / "source_taste_understanding" / "source_database_taste_dossier.json"
    principles_path = root / "datasets" / "source_taste_understanding" / "source_database_generative_principles.jsonl"
    dossier = {}
    if dossier_path.exists():
        try:
            dossier = json.loads(dossier_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            dossier = {}
    principles = []
    if principles_path.exists():
        for line in principles_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            raw = line.strip()
            if not raw:
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                principles.append(row)
    return {"dossier": dossier, "principles": principles}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full presentable composition pipeline.")
    parser.add_argument("--config", default="", help="Optional local config override path.")
    parser.add_argument("--include-reaper", action="store_true", help="Build optional reaper/render pack plan.")
    args = parser.parse_args()
    summary = run_full_pipeline(Path(args.config) if args.config else None, include_reaper=args.include_reaper)
    context = _load_source_understanding_context(ROOT_DIR)
    principles = context["principles"]
    dossier = context["dossier"]
    summary["source_database_principles_cited"] = [str(row.get("principle_id", "")) for row in principles[:5] if str(row.get("principle_id", "")).strip()]
    summary["source_database_rejected_principles"] = list(dossier.get("rejected_principles", [])) if isinstance(dossier, dict) else []
    summary["witness_influence_summary"] = list(dossier.get("witness_influence_summary", [])) if isinstance(dossier, dict) else []
    summary["weak_evidence_areas"] = list(dossier.get("weak_evidence_limits", [])) if isinstance(dossier, dict) else []
    summary["transformation_vs_copy_note"] = str(
        dossier.get("transformation_vs_copy_policy", "Transform source intent; never copy source content directly.")
    ) if isinstance(dossier, dict) else "Transform source intent; never copy source content directly."
    print(f"PIPELINE_STATUS={summary.get('status', 'unknown')}")
    print(f"CANDIDATES_GENERATED={summary.get('candidates_generated', 0)}")
    print(f"SELECTED_CANDIDATE={summary.get('selected_candidate', 'none')}")
    print(f"SELECTED_FULL_MIDI={summary.get('selected_full_midi_path', '')}")
    print(f"SELECTED_STEMS_PATH={summary.get('selected_stems_path', '')}")
    print(f"PRESENTABILITY_SCORE={summary.get('presentability_score', 0.0)}")
    print(f"RATIO_COMPLIANCE_SCORE={summary.get('ratio_compliance_score', 0.0)}")
    print(f"DATABASE_COMPARISON_CONFIDENCE={summary.get('database_comparison_confidence', 0.0)}")
    print(f"SOURCE_DB_PRINCIPLES_CITED={len(summary.get('source_database_principles_cited', []))}")
    print(f"SUMMARY_JSON={json.dumps(summary, ensure_ascii=True)}")
    return 0 if summary.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
