from __future__ import annotations

import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.midi_buddy_generation import generate_buddy_pack_for_extracted_loop

RANKED_JSONL = ROOT_DIR / "datasets" / "source_loop_extraction" / "ranked_extracted_source_loops.jsonl"
OUTPUT_ROOT = ROOT_DIR / "outputs" / "source_loop_midi_buddies_v1"
BEST_PACK_DIR = OUTPUT_ROOT / "best_pack"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _safe_rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT_DIR.resolve()).as_posix()


def main() -> int:
    rows = _read_jsonl(RANKED_JSONL)
    selected = [row for row in rows if bool(row.get("selected_for_midi_buddy_generation", False))]
    if not selected:
        selected = rows[:12]
    selected = [row for row in selected if bool(row.get("local_audio_clip_exists", False))]

    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    clip_manifests: list[dict[str, Any]] = []
    for idx, row in enumerate(selected, start=1):
        clip_result = generate_buddy_pack_for_extracted_loop(
            row,
            clip_index=idx,
            project_root=ROOT_DIR,
            output_root=OUTPUT_ROOT,
        )
        clip_manifests.append(clip_result)

    BEST_PACK_DIR.mkdir(parents=True, exist_ok=True)
    if clip_manifests:
        best_manifest_path = ROOT_DIR / clip_manifests[0]["clip_manifest_path"]
        shutil.copy2(best_manifest_path, BEST_PACK_DIR / "best_clip_manifest.json")

    summary = {
        "generated_at": datetime.now(UTC).isoformat(),
        "selected_actual_loops_count": len(selected),
        "midi_buddy_packs_generated": len(clip_manifests),
        "clip_manifests": clip_manifests,
        "best_pack_dir": _safe_rel(BEST_PACK_DIR),
        "policy": {
            "source_loop_wav_kept_local_only": True,
            "role_separated_midi_written": True,
            "no_direct_source_audio_commit": True,
        },
    }
    summary_path = OUTPUT_ROOT / "source_loop_midi_buddy_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"SOURCE_LOOP_MIDI_BUDDY_OUTPUT_ROOT={_safe_rel(OUTPUT_ROOT)}")
    print(f"SOURCE_LOOP_MIDI_BUDDY_SUMMARY_JSON={_safe_rel(summary_path)}")
    print(f"SELECTED_ACTUAL_LOOPS_COUNT={len(selected)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
