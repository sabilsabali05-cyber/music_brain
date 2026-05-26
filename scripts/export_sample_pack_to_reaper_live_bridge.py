from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

OUTPUT_ROOT = ROOT_DIR / "outputs" / "source_sample_packs"


def _safe_rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT_DIR.resolve()).as_posix()


def _latest_pack_dir() -> Path | None:
    if not OUTPUT_ROOT.exists():
        return None
    dirs = [entry for entry in OUTPUT_ROOT.iterdir() if entry.is_dir()]
    if not dirs:
        return None
    dirs.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return dirs[0]


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def build_reaper_bridge_manifest(pack_dir: Path) -> tuple[dict[str, Any], Path]:
    manifest_path = pack_dir / "manifest.json"
    pack_manifest = _load_json(manifest_path)
    audio_loops = pack_manifest.get("audio_loops", [])
    midi_starters = pack_manifest.get("midi_starters", [])
    if not isinstance(audio_loops, list):
        audio_loops = []
    if not isinstance(midi_starters, list):
        midi_starters = []

    tracks: list[dict[str, Any]] = []
    for idx, item in enumerate(audio_loops):
        rel_path = str(item.get("path", "")).strip()
        if not rel_path:
            continue
        tracks.append(
            {
                "track_name": f"AI Brain Audio Loop {idx + 1}",
                "track_type": "audio",
                "source_path": rel_path,
                "overwrite_user_track": False,
            }
        )
    for idx, item in enumerate(midi_starters):
        rel_path = str(item.get("path", "")).strip()
        if not rel_path:
            continue
        tracks.append(
            {
                "track_name": f"AI Brain MIDI Starter {idx + 1}",
                "track_type": "midi",
                "source_path": rel_path,
                "overwrite_user_track": False,
            }
        )

    bridge_manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "pack_id": str(pack_manifest.get("pack_id", pack_dir.name)),
        "source_manifest": _safe_rel(manifest_path),
        "track_namespace": "AI Brain",
        "overwrite_user_tracks": False,
        "tracks": tracks,
    }
    out_path = pack_dir / "reaper_live_bridge_manifest.json"
    out_path.write_text(json.dumps(bridge_manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return bridge_manifest, out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Create REAPER live bridge manifest for latest source sample pack.")
    parser.add_argument("--pack-dir", help="Optional pack directory; defaults to latest pack.", default="")
    args = parser.parse_args()

    if args.pack_dir:
        pack_dir = (ROOT_DIR / args.pack_dir).resolve(strict=False)
    else:
        latest = _latest_pack_dir()
        if latest is None:
            print("ERROR=No source sample pack directory found under outputs/source_sample_packs")
            return 1
        pack_dir = latest

    if not (pack_dir / "manifest.json").exists():
        print(f"ERROR=manifest.json missing in {pack_dir}")
        return 1

    bridge_manifest, out_path = build_reaper_bridge_manifest(pack_dir)
    print(f"REAPER_SAMPLE_PACK_BRIDGE_MANIFEST={_safe_rel(out_path)}")
    print(f"REAPER_SAMPLE_PACK_TRACKS={len(bridge_manifest['tracks'])}")
    print("REAPER_SAMPLE_PACK_OVERWRITE_USER_TRACKS=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
