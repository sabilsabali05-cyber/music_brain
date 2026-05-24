from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _latest_round_id() -> str:
    pointer = ROOT_DIR / "datasets" / "beat_battle_agent" / "manual_rounds" / "latest_round_manifest.txt"
    if not pointer.exists():
        return ""
    manifest_path = Path(pointer.read_text(encoding="utf-8").strip())
    if not manifest_path.is_absolute():
        manifest_path = (ROOT_DIR / manifest_path).resolve()
    if not manifest_path.exists():
        return ""
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    return str(payload.get("round_id", "")).strip() if isinstance(payload, dict) else ""


def main() -> int:
    round_id = _latest_round_id()
    if not round_id:
        print("BLOCKER=missing_manual_round_manifest")
        return 1
    pack_path = ROOT_DIR / "outputs" / "beat_battle_agent" / round_id / "submission_pack" / "submission_pack.json"
    if not pack_path.exists():
        print("BLOCKER=missing_submission_pack")
        return 1
    payload = json.loads(pack_path.read_text(encoding="utf-8"))
    if payload.get("synplant_included", False):
        print("BLOCKER=synplant_not_allowed_in_submission_pack")
        return 1
    print(f"ROUND_ID={round_id}")
    print(f"SUBMISSION_PACK_PATH={pack_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
