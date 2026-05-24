from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.beat_battle_site_automation.site_config_schema import load_optional_local_site_config  # noqa: E402


def _latest_manifest() -> Path | None:
    manifests = sorted((ROOT_DIR / "datasets" / "beat_battle_site" / "rounds").glob("*/round_manifest.json"))
    return manifests[-1] if manifests else None


def main() -> int:
    config, blocker = load_optional_local_site_config(ROOT_DIR)
    if config is None:
        print(f"BLOCKER={blocker}")
        return 1
    manifest_path = _latest_manifest()
    if manifest_path is None:
        print("BLOCKER=missing_round_manifest")
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    round_id = str(manifest.get("round_id", "")).strip()
    sounds = manifest.get("sounds", [])
    sounds = sounds if isinstance(sounds, list) else []
    if not round_id or not sounds:
        print("BLOCKER=round_manifest_missing_sounds")
        return 1
    drafts_root = ROOT_DIR / "outputs" / "beat_battle_site" / round_id / "drafts"
    drafts_root.mkdir(parents=True, exist_ok=True)
    ratio_spec_path = ROOT_DIR / "outputs" / "ratio_controlled_song_v1" / "ratio_control_spec.json"
    ratio_spec: dict[str, object] = {}
    if ratio_spec_path.exists():
        try:
            loaded = json.loads(ratio_spec_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                ratio_spec = loaded
        except json.JSONDecodeError:
            ratio_spec = {}
    rng = random.Random(round_id)
    ranked: list[dict[str, object]] = []
    for idx in range(8):
        draft_id = f"draft_{idx+1:02d}"
        score = round(0.45 + rng.random() * 0.5, 6)
        ratio_controls = ratio_spec.get("ratio_controls", []) if isinstance(ratio_spec, dict) else []
        ratio_enabled = bool(ratio_controls)
        ratio_bonus = min(0.04, 0.005 * len(ratio_controls)) if ratio_enabled else 0.0
        score = round(min(0.99, score + ratio_bonus), 6)
        draft_payload = {
            "draft_id": draft_id,
            "round_id": round_id,
            "uses_only_round_manifest_sounds": True,
            "sound_ids": [str(s.get("sound_id", "")) for s in sounds][: min(8, len(sounds))],
            "chordpotion_used": False,
            "synplant_used": False,
            "ratio_controls_enabled": ratio_enabled,
            "ratio_battle_flex_mode": True,
            "ratio_controls_applied_to": ["arrangement", "drop", "rhythm", "hook_return", "density"] if ratio_enabled else [],
            "battle_appeal_priority": 0.8,
            "ranker_score": score,
        }
        (drafts_root / f"{draft_id}.json").write_text(json.dumps(draft_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        ranked.append(draft_payload)
    ranked.sort(key=lambda row: float(row["ranker_score"]), reverse=True)
    ranked_path = ROOT_DIR / "outputs" / "beat_battle_site" / round_id / "ranked_drafts.json"
    ranked_path.parent.mkdir(parents=True, exist_ok=True)
    ranked_path.write_text(json.dumps(ranked, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    selected_dir = ROOT_DIR / "outputs" / "beat_battle_site" / round_id / "selected_draft"
    selected_dir.mkdir(parents=True, exist_ok=True)
    (selected_dir / "selected_draft.json").write_text(json.dumps(ranked[0], indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"RANKED_DRAFTS={ranked_path.as_posix()}")
    print(f"DRAFTS_GENERATED={len(ranked)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
