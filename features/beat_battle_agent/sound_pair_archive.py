from __future__ import annotations

import json
import shutil
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .sound_pair_record_schema import BattleSoundPairRecord, SoundPairGenerationStatus, now_utc_iso


LOCAL_BATTLE_RECORDS_ROOT = "local_battle_records"
ROUND_MANIFEST_GLOB = "datasets/beat_battle_site/rounds/*/round_manifest.json"
SYNTPLANT_LOCAL_CONFIG_PATH = "config/synplant/sound_pair_render.local.json"
AUDIO_EXTENSIONS = {".wav", ".mp3", ".aif", ".aiff", ".flac", ".ogg", ".m4a"}
REQUIRED_LISTENING_QUESTIONS = [
    "Which version wins for this battle sound pair? (provided/synplant/tie/skip)",
    "How well does the Synplant variation preserve core character? (1-5)",
    "How much does the Synplant variation improve uniqueness? (1-5)",
    "Is the Synplant variation mix-ready? (yes/no)",
    "What should be changed before final use?",
]


@dataclass(frozen=True)
class BuildSoundPairArchiveResult:
    blocker: str
    round_id: str
    round_manifest_path: str
    provided_sounds_logged_count: int
    synplant_variations_generated_count: int
    synplant_variations_pending_count: int
    listening_sheet_md_path: str
    listening_sheet_html_path: str
    review_notes_local_json_path: str
    records: list[BattleSoundPairRecord]


def load_latest_or_manual_round_manifest(project_root: Path, manual_manifest: str = "") -> tuple[Path | None, str]:
    if manual_manifest:
        manual_path = (project_root / manual_manifest).resolve()
        if not manual_path.exists():
            return None, "missing_manual_round_config"
        return manual_path, ""
    manifests = sorted((project_root).glob(ROUND_MANIFEST_GLOB), key=lambda item: item.stat().st_mtime, reverse=True)
    if not manifests:
        return None, "missing_manual_round_config"
    return manifests[0].resolve(), ""


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    return payload


def _repo_rel(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except Exception:  # noqa: BLE001
        return path.as_posix()


def _safe_audio_ext(path: Path) -> str:
    ext = path.suffix.lower()
    return ext if ext in AUDIO_EXTENSIONS else ".wav"


def _audio_is_readable(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    if path.suffix.lower() != ".wav":
        return path.stat().st_size > 0
    try:
        with wave.open(str(path), "rb") as wav_handle:
            return wav_handle.getnframes() > 0 and wav_handle.getframerate() > 0
    except Exception:  # noqa: BLE001
        return False


def _audio_is_non_silent(path: Path) -> bool:
    if not path.exists():
        return False
    if path.suffix.lower() != ".wav":
        return path.stat().st_size > 256
    try:
        with wave.open(str(path), "rb") as wav_handle:
            frames = wav_handle.readframes(min(4096, wav_handle.getnframes()))
            return any(byte != 0 for byte in frames)
    except Exception:  # noqa: BLE001
        return False


def _load_synplant_local_config(project_root: Path) -> tuple[bool, dict[str, str]]:
    config_path = (project_root / SYNTPLANT_LOCAL_CONFIG_PATH).resolve()
    if not config_path.exists():
        return False, {}
    try:
        payload = _read_json(config_path)
    except Exception:  # noqa: BLE001
        return False, {}
    enabled = bool(payload.get("enabled", False))
    source_map = payload.get("variation_source_paths_by_sound_id", {})
    if not isinstance(source_map, dict):
        source_map = {}
    return enabled, {str(key): str(value) for key, value in source_map.items() if str(key).strip() and str(value).strip()}


def build_sound_pair_archive(project_root: Path, manual_manifest: str = "") -> BuildSoundPairArchiveResult:
    manifest_path, blocker = load_latest_or_manual_round_manifest(project_root, manual_manifest=manual_manifest)
    if manifest_path is None:
        return BuildSoundPairArchiveResult(
            blocker=blocker or "missing_manual_round_config",
            round_id="",
            round_manifest_path="",
            provided_sounds_logged_count=0,
            synplant_variations_generated_count=0,
            synplant_variations_pending_count=0,
            listening_sheet_md_path="",
            listening_sheet_html_path="",
            review_notes_local_json_path="",
            records=[],
        )

    manifest = _read_json(manifest_path)
    round_id = str(manifest.get("round_id", "")).strip()
    sounds = manifest.get("sounds", [])
    if not round_id or not isinstance(sounds, list):
        return BuildSoundPairArchiveResult(
            blocker="invalid_round_manifest",
            round_id=round_id,
            round_manifest_path=_repo_rel(project_root, manifest_path),
            provided_sounds_logged_count=0,
            synplant_variations_generated_count=0,
            synplant_variations_pending_count=0,
            listening_sheet_md_path="",
            listening_sheet_html_path="",
            review_notes_local_json_path="",
            records=[],
        )

    round_root = (project_root / LOCAL_BATTLE_RECORDS_ROOT / round_id).resolve()
    provided_dir = round_root / "provided_sounds"
    synplant_dir = round_root / "synplant_variations"
    provided_dir.mkdir(parents=True, exist_ok=True)
    synplant_dir.mkdir(parents=True, exist_ok=True)
    listening_sheet_html = round_root / "listening_sheet.html"
    listening_sheet_md = round_root / "listening_sheet.md"
    review_notes_local_json = round_root / "review_notes.local.json"

    synplant_enabled, synplant_sources = _load_synplant_local_config(project_root)
    records: list[BattleSoundPairRecord] = []
    generated_count = 0
    pending_count = 0

    for idx, item in enumerate(sounds, start=1):
        if not isinstance(item, dict):
            continue
        sound_id = str(item.get("sound_id", f"provided_{idx:03d}")).strip() or f"provided_{idx:03d}"
        source_kind = str(item.get("source_kind", "unknown")).strip() or "unknown"
        source_ref = str(item.get("source_ref", "")).strip()
        raw_audio_path = str(item.get("raw_audio_path", "")).strip()
        source_path = Path(raw_audio_path) if raw_audio_path else Path("")
        original_exists = bool(raw_audio_path) and source_path.exists() and source_path.is_file()
        provided_copy_path = provided_dir / f"{sound_id}{_safe_audio_ext(source_path if original_exists else Path(sound_id + '.wav'))}"
        if original_exists:
            shutil.copy2(source_path, provided_copy_path)
            readable = _audio_is_readable(provided_copy_path)
        else:
            readable = False

        variation_id = f"{sound_id}_synplant_001"
        status = SoundPairGenerationStatus.pending_synplant_config.value
        synplant_blocker = "synplant_not_configured"
        variation_path = synplant_dir / f"{variation_id}.wav"
        variation_exists = False
        variation_non_silent = False

        if not readable:
            status = SoundPairGenerationStatus.failed.value
            synplant_blocker = "provided_sound_unreadable"
        elif synplant_enabled:
            configured_source = synplant_sources.get(sound_id, "")
            if configured_source:
                candidate = Path(configured_source)
                if candidate.exists() and candidate.is_file():
                    shutil.copy2(candidate, variation_path)
                    variation_exists = variation_path.exists()
                    variation_non_silent = _audio_is_non_silent(variation_path)
                    if variation_exists and variation_non_silent:
                        status = SoundPairGenerationStatus.generated.value
                        synplant_blocker = ""
                        generated_count += 1
                    else:
                        status = SoundPairGenerationStatus.failed.value
                        synplant_blocker = "synplant_variation_silent_or_missing"
                else:
                    status = SoundPairGenerationStatus.failed.value
                    synplant_blocker = "synplant_variation_source_missing"
            else:
                status = SoundPairGenerationStatus.failed.value
                synplant_blocker = "missing_synplant_variation_source_for_sound"
        else:
            pending_count += 1

        record = BattleSoundPairRecord(
            record_id=f"{round_id}:{variation_id}",
            round_id=round_id,
            created_at_utc=now_utc_iso(),
            source_round_manifest_path=_repo_rel(project_root, manifest_path),
            provided_sound_id=sound_id,
            provided_source_kind=source_kind,
            provided_source_ref=source_ref,
            provided_original_path="<LOCAL_AUDIO_PATH>" if raw_audio_path else "",
            provided_local_copy_path=_repo_rel(project_root, provided_copy_path) if original_exists else "",
            provided_audio_readable=readable,
            synplant_variation_id=variation_id,
            synplant_generation_status=status,
            synplant_blocker=synplant_blocker,
            synplant_task_created=True,
            synplant_variation_path=_repo_rel(project_root, variation_path),
            synplant_variation_exists=variation_exists,
            synplant_variation_non_silent=variation_non_silent,
            listening_sheet_md_path=_repo_rel(project_root, listening_sheet_md),
            listening_sheet_html_path=_repo_rel(project_root, listening_sheet_html),
            review_notes_local_json_path=_repo_rel(project_root, review_notes_local_json),
            listening_questions=REQUIRED_LISTENING_QUESTIONS,
        )
        records.append(record)

    return BuildSoundPairArchiveResult(
        blocker="",
        round_id=round_id,
        round_manifest_path=_repo_rel(project_root, manifest_path),
        provided_sounds_logged_count=len(records),
        synplant_variations_generated_count=generated_count,
        synplant_variations_pending_count=pending_count,
        listening_sheet_md_path=_repo_rel(project_root, listening_sheet_md),
        listening_sheet_html_path=_repo_rel(project_root, listening_sheet_html),
        review_notes_local_json_path=_repo_rel(project_root, review_notes_local_json),
        records=records,
    )
