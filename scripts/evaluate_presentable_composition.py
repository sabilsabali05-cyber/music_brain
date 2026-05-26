from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.composition_projects import evaluate_presentable


def main() -> int:
    payload = evaluate_presentable()
    print(f"PRESENTABLE_PASS={str(payload.get('pass', False)).lower()}")
    print(f"PRESENTABILITY_SCORE={payload.get('presentability_score', 0.0)}")
    print(f"RATIO_COMPLIANCE_SCORE={payload.get('ratio_compliance_score', 0.0)}")
    print(f"SELECTED_CANDIDATE={payload.get('selected_candidate', 'none')}")
    return 0 if payload.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
