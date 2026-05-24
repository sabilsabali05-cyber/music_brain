from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.beat_battle_agent.agent_config_schema import load_optional_local_agent_config  # noqa: E402
from features.beat_battle_agent.round_beat_generator import generate_round_beats  # noqa: E402


def _latest_manual_round_id() -> str:
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
    config, blocker = load_optional_local_agent_config(ROOT_DIR)
    if config is None:
        print(f"BLOCKER={blocker}")
        return 1
    round_id = _latest_manual_round_id()
    if not round_id:
        print("BLOCKER=missing_manual_round_manifest")
        return 1
    result = generate_round_beats(ROOT_DIR, config, round_id)
    if result.get("blocker"):
        print(f"BLOCKER={result['blocker']}")
        return 1
    print(f"ROUND_ID={round_id}")
    print(f"DRAFTS_GENERATED={result.get('drafts_generated', 0)}")
    print(f"SUBMISSION_PACK_PATH={result.get('submission_pack_path', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
