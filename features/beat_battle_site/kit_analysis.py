from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class KitAnalysisResult:
    round_id: str
    sounds_count: int
    analysis_mode: str
    inferred_tags: list[str]
    sound_summaries: list[dict[str, Any]]


def analyze_round_manifest(manifest_path: Path) -> KitAnalysisResult:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    round_id = str(payload.get("round_id", "unknown"))
    sounds = payload.get("sounds", [])
    sounds = sounds if isinstance(sounds, list) else []
    analysis_mode = "filename_metadata_only"
    try:
        import librosa  # type: ignore # noqa: F401

        analysis_mode = "audio_libs_available"
    except Exception:
        analysis_mode = "filename_metadata_only"
    sound_summaries: list[dict[str, Any]] = []
    tags: set[str] = set()
    for item in sounds:
        if not isinstance(item, dict):
            continue
        source = str(item.get("source_ref", ""))
        source_lower = source.lower()
        name = source_lower.rsplit("/", 1)[-1]
        if "kick" in name:
            tags.add("kick")
        if "snare" in name:
            tags.add("snare")
        if "hat" in name:
            tags.add("hat")
        if "bass" in name:
            tags.add("bass")
        sound_summaries.append(
            {
                "sound_id": item.get("sound_id", ""),
                "source_kind": item.get("source_kind", ""),
                "inferred_name": name or "unknown",
            }
        )
    return KitAnalysisResult(
        round_id=round_id,
        sounds_count=len(sound_summaries),
        analysis_mode=analysis_mode,
        inferred_tags=sorted(tags),
        sound_summaries=sound_summaries,
    )
