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

RANKED_JSONL = ROOT_DIR / "datasets" / "source_loop_extraction" / "ranked_extracted_source_loops.jsonl"
MIDI_ROOT = ROOT_DIR / "outputs" / "source_loop_midi_buddies_v1"
LOCAL_REAPER_PACK = ROOT_DIR / "local_source_audio_study" / "reaper_loop_buddy_packs" / "latest"
REPORT_DIR = ROOT_DIR / "reports" / "source_loop_midi_buddies"
REPORT_MD = REPORT_DIR / "reaper_pack_report.md"
REPORT_JSON = REPORT_DIR / "reaper_pack_report.json"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


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
    selected_rows = [row for row in _read_jsonl(RANKED_JSONL) if bool(row.get("selected_for_midi_buddy_generation", False))]
    summary = _read_json(MIDI_ROOT / "source_loop_midi_buddy_summary.json")
    clip_manifests = summary.get("clip_manifests", []) if isinstance(summary.get("clip_manifests"), list) else []

    if LOCAL_REAPER_PACK.exists():
        shutil.rmtree(LOCAL_REAPER_PACK)
    LOCAL_REAPER_PACK.mkdir(parents=True, exist_ok=True)
    drag_files: list[str] = []

    for idx, clip in enumerate(clip_manifests, start=1):
        clip_dir = Path(str(clip.get("clip_dir", "")))
        if clip_dir.is_absolute():
            source_clip_dir = clip_dir
        else:
            source_clip_dir = ROOT_DIR / clip_dir
        if not source_clip_dir.exists():
            continue
        target_clip = LOCAL_REAPER_PACK / f"clip_{idx:03d}"
        target_clip.mkdir(parents=True, exist_ok=True)
        for midi_file in source_clip_dir.glob("**/*.mid"):
            rel = midi_file.relative_to(source_clip_dir)
            target = target_clip / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(midi_file, target)
            drag_files.append(_safe_rel(target))

    # Include local source loop wav files in local pack only.
    for idx, row in enumerate(selected_rows, start=1):
        local_rel = str(row.get("local_clip_relpath", "")).strip()
        if not local_rel:
            continue
        src_wav = ROOT_DIR / local_rel
        if not src_wav.exists():
            continue
        target_wav = LOCAL_REAPER_PACK / f"clip_{idx:03d}" / "source_loop.wav"
        target_wav.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_wav, target_wav)
        drag_files.append(_safe_rel(target_wav))

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "reaper_pack_folder": _safe_rel(LOCAL_REAPER_PACK),
        "drag_files": sorted(drag_files),
        "source_audio_committed": False,
        "private_paths_in_committed_outputs": False,
        "notes": [
            "Pack is local-only and REAPER-ready.",
            "source_loop.wav files remain in ignored local paths only.",
        ],
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = [
        "# REAPER Pack Report",
        "",
        f"- generated_at: `{payload['generated_at']}`",
        f"- reaper_pack_folder: `{payload['reaper_pack_folder']}`",
        f"- source_audio_committed: `{payload['source_audio_committed']}`",
        f"- private_paths_in_committed_outputs: `{payload['private_paths_in_committed_outputs']}`",
        "",
        "## Drag Into REAPER",
    ]
    lines.extend([f"- `{item}`" for item in payload["drag_files"][:200]])
    REPORT_MD.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    print(f"REAPER_PACK_FOLDER={payload['reaper_pack_folder']}")
    print(f"REAPER_PACK_REPORT_MD={_safe_rel(REPORT_MD)}")
    print(f"REAPER_PACK_REPORT_JSON={_safe_rel(REPORT_JSON)}")
    print(f"REAPER_DRAG_FILES_COUNT={len(payload['drag_files'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
