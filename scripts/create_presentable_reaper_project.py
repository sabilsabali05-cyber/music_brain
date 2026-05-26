from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.composition_projects import create_reaper_plan


def main() -> int:
    payload = create_reaper_plan()
    print(f"REAPER_PROJECT_PATH={payload.get('reaper_project_path', '')}")
    print(f"RENDER_PACK_PATH={payload.get('render_pack_path', '')}")
    print("WAV_RENDERED=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
