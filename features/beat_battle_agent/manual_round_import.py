from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

AUDIO_SUFFIXES = {".wav", ".aif", ".aiff", ".flac", ".mp3", ".ogg", ".m4a"}
LOCAL_CONFIG_PATH = Path("config/beat_battle_manual_round.local.json")


def _safe_round_id(raw: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in raw.strip())
    return cleaned or "unknown_round"


def _hash_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def _load_local_manual_round_config(project_root: Path) -> tuple[dict[str, Any] | None, str]:
    path = project_root / LOCAL_CONFIG_PATH
    if not path.exists():
        return None, "missing_manual_round_config"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None, "invalid_manual_round_config"
    if not isinstance(payload, dict):
        return None, "invalid_manual_round_config"
    return payload, ""


def import_manual_round(project_root: Path) -> dict[str, Any]:
    config, blocker = _load_local_manual_round_config(project_root)
    if config is None:
        return {"ok": False, "blocker": blocker, "sounds_imported": 0}

    round_id = _safe_round_id(str(config.get("round_id", "")))
    round_sounds_folder = Path(str(config.get("round_sounds_folder", "")).strip())
    if not round_sounds_folder:
        return {"ok": False, "blocker": "missing_round_sounds_folder", "sounds_imported": 0}
    if not round_sounds_folder.is_absolute():
        round_sounds_folder = (project_root / round_sounds_folder).resolve()
    if not round_sounds_folder.exists():
        return {"ok": False, "blocker": "missing_round_sounds_folder", "sounds_imported": 0}

    sound_paths = sorted([path for path in round_sounds_folder.iterdir() if path.is_file() and path.suffix.lower() in AUDIO_SUFFIXES])
    if not sound_paths:
        return {"ok": False, "blocker": "no_round_sounds_found", "sounds_imported": 0}

    seen_hashes: set[str] = set()
    sounds: list[dict[str, Any]] = []
    for index, path in enumerate(sound_paths, start=1):
        file_hash = _hash_file(path)
        if file_hash in seen_hashes:
            continue
        seen_hashes.add(file_hash)
        sounds.append(
            {
                "sound_id": f"{round_id}_snd_{index:02d}",
                "filename": path.name,
                "sha256": file_hash,
                "bytes": path.stat().st_size,
                "extension": path.suffix.lower(),
                "source_type": "provided_round_sound",
                "source_path_redacted": True,
                "source_path": "<REDACTED_LOCAL_PATH>",
                "submission_allowed": True,
                "study_allowed": True,
            }
        )

    dataset_root = project_root / "datasets" / "beat_battle_agent" / "manual_rounds" / round_id
    dataset_root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "round_id": round_id,
        "import_mode": "manual_local_folder",
        "source_folder_redacted": True,
        "source_folder": "<REDACTED_LOCAL_FOLDER>",
        "sounds_imported": len(sounds),
        "sounds": sounds,
    }
    manifest_path = dataset_root / "round_manifest.redacted.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    latest_pointer = project_root / "datasets" / "beat_battle_agent" / "manual_rounds" / "latest_round_manifest.txt"
    latest_pointer.parent.mkdir(parents=True, exist_ok=True)
    latest_pointer.write_text(manifest_path.as_posix(), encoding="utf-8")

    report_path = project_root / "reports" / "beat_battle_agent" / "manual_round_import_status.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        "\n".join(
            [
                "# Manual Round Import Status",
                "",
                f"- round_id: `{round_id}`",
                f"- sounds_imported: `{len(sounds)}`",
                "- source_path_redacted: `true`",
                "- raw_round_sounds_committed: `false`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {"ok": True, "blocker": "", "round_id": round_id, "sounds_imported": len(sounds), "manifest_path": manifest_path.as_posix()}
