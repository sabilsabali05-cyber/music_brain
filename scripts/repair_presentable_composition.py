from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.composition_projects import repair_selected


def main() -> int:
    payload = repair_selected()
    print(f"REPAIR_APPLIED={str(payload.get('repair_applied', False)).lower()}")
    print(f"PRESENTABILITY_BEFORE={payload.get('presentability_before', 0.0)}")
    print(f"PRESENTABILITY_AFTER={payload.get('presentability_after', 0.0)}")
    print(f"SELECTED_CANDIDATE={payload.get('selected_candidate_after_repair', 'none')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
