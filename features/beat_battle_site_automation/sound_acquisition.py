from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .site_config_schema import BeatBattleRankedSiteConfig


AUDIO_EXTENSIONS = {".wav", ".mp3", ".aif", ".aiff", ".flac", ".ogg", ".m4a"}


@dataclass(frozen=True)
class SoundAcquisitionResult:
    round_id: str
    sounds_acquired: bool
    acquired_count: int
    manifest_path: str
    raw_audio_folder: str
    blocker: str | None
    strategy_summary: list[dict[str, Any]]


def _is_audio_path(path: Path) -> bool:
    return path.suffix.lower() in AUDIO_EXTENSIONS


def acquire_round_sounds(
    *,
    config: BeatBattleRankedSiteConfig,
    project_root: Path,
    round_id: str,
    round_sound_urls: list[str],
) -> SoundAcquisitionResult:
    raw_dir = (project_root / config.paths.local_raw_audio_dir / round_id).resolve()
    raw_dir.mkdir(parents=True, exist_ok=True)
    round_manifest_path = (project_root / config.paths.round_manifest_root / round_id / "round_manifest.json").resolve()
    round_manifest_path.parent.mkdir(parents=True, exist_ok=True)

    strategy_summary: list[dict[str, Any]] = []
    sounds: list[dict[str, Any]] = []

    if "snapshot_sound_links" in config.acquisition.strategies:
        for idx, url in enumerate(round_sound_urls):
            sounds.append(
                {
                    "sound_id": f"snapshot_{idx+1:03d}",
                    "source_kind": "round_snapshot_url",
                    "source_ref": url,
                    "raw_audio_path": "",
                    "copied_to_local_raw_audio": False,
                }
            )
        strategy_summary.append({"strategy": "snapshot_sound_links", "count": len(round_sound_urls)})

    if "manual_file_import" in config.acquisition.strategies:
        imported = 0
        for idx, source_path in enumerate(config.acquisition.manual_sound_file_paths):
            candidate = Path(source_path)
            if not candidate.exists() or not candidate.is_file() or not _is_audio_path(candidate):
                continue
            target = raw_dir / f"manual_{idx+1:03d}{candidate.suffix.lower()}"
            shutil.copy2(candidate, target)
            sounds.append(
                {
                    "sound_id": f"manual_{idx+1:03d}",
                    "source_kind": "manual_file_import",
                    "source_ref": "<LOCAL_AUDIO_PATH>",
                    "raw_audio_path": target.as_posix(),
                    "copied_to_local_raw_audio": True,
                }
            )
            imported += 1
        strategy_summary.append({"strategy": "manual_file_import", "count": imported})

    if "local_round_folder_scan" in config.acquisition.strategies:
        folder = (project_root / config.acquisition.local_round_sound_folder / round_id).resolve()
        count = 0
        if folder.exists():
            for idx, source in enumerate(sorted(folder.glob("*"))):
                if not source.is_file() or not _is_audio_path(source):
                    continue
                target = raw_dir / f"scanned_{idx+1:03d}{source.suffix.lower()}"
                shutil.copy2(source, target)
                sounds.append(
                    {
                        "sound_id": f"scanned_{idx+1:03d}",
                        "source_kind": "local_round_folder_scan",
                        "source_ref": "<LOCAL_AUDIO_PATH>",
                        "raw_audio_path": target.as_posix(),
                        "copied_to_local_raw_audio": True,
                    }
                )
                count += 1
        strategy_summary.append({"strategy": "local_round_folder_scan", "count": count})

    manifest = {
        "round_id": round_id,
        "policy": {
            "only_active_round_sounds": True,
            "raw_audio_stored_local_only": True,
            "no_unauthorized_audio_training": True,
        },
        "sounds": sounds,
    }
    round_manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    acquired_count = len(sounds)
    return SoundAcquisitionResult(
        round_id=round_id,
        sounds_acquired=acquired_count > 0,
        acquired_count=acquired_count,
        manifest_path=round_manifest_path.as_posix(),
        raw_audio_folder=raw_dir.as_posix(),
        blocker=None if acquired_count > 0 else "no_round_sounds_acquired",
        strategy_summary=strategy_summary,
    )
