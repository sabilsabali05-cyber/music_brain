from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.composition_projects import evaluate_presentable


def main() -> int:
    payload = evaluate_presentable()
    print(f"DOES_IT_REALIZE_THE_BRIEF={str(payload.get('does_it_realize_the_brief', False)).lower()}")
    print(f"CRITIQUE_SUMMARY={payload.get('critique_summary', '')}")
    print(f"WHERE_IT_BETRAYS_THE_BRIEF_COUNT={len(payload.get('where_it_betrays_the_brief', []))}")
    return 0 if payload.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
