from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.composition_projects import rank_candidates


def main() -> int:
    payload = rank_candidates()
    print(f"CANDIDATES_RANKED={payload.get('candidates_ranked', 0)}")
    print(f"SELECTED_CANDIDATE={payload.get('selected_candidate', 'none')}")
    print(f"SELECTED_FULL_MIDI={payload.get('selected_full_midi', '')}")
    print(f"SELECTED_STEMS_PATH={payload.get('selected_stems_path', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
