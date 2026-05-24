from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any


class SoundPairGenerationStatus(str, Enum):
    generated = "generated"
    pending_synplant_config = "pending_synplant_config"
    failed = "failed"
    skipped = "skipped"


@dataclass(frozen=True)
class BattleSoundPairRecord:
    record_id: str
    round_id: str
    created_at_utc: str
    source_round_manifest_path: str
    provided_sound_id: str
    provided_source_kind: str
    provided_source_ref: str
    provided_original_path: str
    provided_local_copy_path: str
    provided_audio_readable: bool
    synplant_variation_id: str
    synplant_generation_status: str
    synplant_blocker: str
    synplant_task_created: bool
    synplant_variation_path: str
    synplant_variation_exists: bool
    synplant_variation_non_silent: bool
    listening_sheet_md_path: str
    listening_sheet_html_path: str
    review_notes_local_json_path: str
    listening_questions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def now_utc_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def validate_generation_status(value: str) -> str:
    normalized = value.strip()
    allowed = {item.value for item in SoundPairGenerationStatus}
    if normalized not in allowed:
        raise ValueError(f"invalid generation status: {value}")
    return normalized


def append_records_jsonl(path: Path, rows: list[BattleSoundPairRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            validate_generation_status(row.synplant_generation_status)
            handle.write(json.dumps(row.to_dict(), ensure_ascii=True) + "\n")


def count_by_status(rows: list[BattleSoundPairRecord]) -> dict[str, int]:
    counts = {item.value: 0 for item in SoundPairGenerationStatus}
    for row in rows:
        status = validate_generation_status(row.synplant_generation_status)
        counts[status] += 1
    return counts
