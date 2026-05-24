from __future__ import annotations

import json
import wave
from pathlib import Path

from scripts.create_battle_sound_pair_record import run_create_battle_sound_pair_record


def _write_test_wav(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_handle:
        wav_handle.setnchannels(1)
        wav_handle.setsampwidth(2)
        wav_handle.setframerate(44100)
        wav_handle.writeframes(b"\x01\x00" * 4096)


def test_create_sound_pair_record_safe_fails_without_round_manifest(tmp_path: Path) -> None:
    payload = run_create_battle_sound_pair_record(tmp_path)
    assert payload["sound_pair_record_created"] is False
    assert "missing_manual_round_config" in payload["blockers"]


def test_create_sound_pair_record_builds_pending_records(tmp_path: Path) -> None:
    source_audio = tmp_path / "source.wav"
    _write_test_wav(source_audio)
    manifest = {
        "round_id": "round_001",
        "sounds": [
            {
                "sound_id": "manual_001",
                "source_kind": "manual_file_import",
                "source_ref": "<LOCAL_AUDIO_PATH>",
                "raw_audio_path": source_audio.as_posix(),
            }
        ],
    }
    manifest_path = tmp_path / "datasets" / "beat_battle_site" / "rounds" / "round_001" / "round_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    payload = run_create_battle_sound_pair_record(tmp_path)
    assert payload["sound_pair_record_created"] is True
    assert payload["provided_sounds_logged_count"] == 1
    assert payload["synplant_variations_pending_count"] == 1
