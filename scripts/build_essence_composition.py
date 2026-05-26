from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.composition_projects import run_full_pipeline  # noqa: E402


def main() -> int:
    summary = run_full_pipeline(include_reaper=True)
    print(f"ESSENCE_PIPELINE_STATUS={summary.get('status', 'unknown')}")
    print(f"DRAFT_UNDERSTANDING_DOSSIER={summary.get('draft_understanding_dossier_path', '')}")
    print(f"DATABASE_UNDERSTANDING_DOSSIER={summary.get('database_understanding_dossier_path', '')}")
    print(f"COMPOSITION_BRIEF_PATH={summary.get('composition_brief_path', '')}")
    print(f"FINAL_CRITIQUE_PATH={summary.get('final_critique_path', '')}")
    print(f"SUMMARY_JSON={json.dumps(summary, ensure_ascii=True)}")
    return 0 if summary.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
