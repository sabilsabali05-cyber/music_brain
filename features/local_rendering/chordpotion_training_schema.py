from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class ChordPotionTrainingRow:
    input_harmony_features: dict
    target_intent: dict
    theory_profile_features: dict
    texture_profile_features: dict
    preset_id: str
    transformed_output_features: dict
    machine_scores: dict
    user_rating: float
    user_notes: str
    keep_or_reject: str
    too_busy: bool
    too_plain: bool
    supports_harmony: bool
    supports_groove: bool
    emotional_value: float
    final_label: str
    provenance: dict

    def as_dict(self) -> dict:
        return asdict(self)


def load_training_rows(path: Path) -> list[ChordPotionTrainingRow]:
    if not path.exists():
        return []
    rows: list[ChordPotionTrainingRow] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text:
            continue
        payload = json.loads(text)
        rows.append(
            ChordPotionTrainingRow(
                input_harmony_features=dict(payload.get("input_harmony_features", {})),
                target_intent=dict(payload.get("target_intent", {})),
                theory_profile_features=dict(payload.get("theory_profile_features", {})),
                texture_profile_features=dict(payload.get("texture_profile_features", {})),
                preset_id=str(payload.get("preset_id", "")),
                transformed_output_features=dict(payload.get("transformed_output_features", {})),
                machine_scores=dict(payload.get("machine_scores", {})),
                user_rating=float(payload.get("user_rating", 0.0) or 0.0),
                user_notes=str(payload.get("user_notes", "")),
                keep_or_reject=str(payload.get("keep_or_reject", "")),
                too_busy=bool(payload.get("too_busy", False)),
                too_plain=bool(payload.get("too_plain", False)),
                supports_harmony=bool(payload.get("supports_harmony", False)),
                supports_groove=bool(payload.get("supports_groove", False)),
                emotional_value=float(payload.get("emotional_value", 0.0) or 0.0),
                final_label=str(payload.get("final_label", "")),
                provenance=dict(payload.get("provenance", {})),
            )
        )
    return rows


def append_training_row(path: Path, row: ChordPotionTrainingRow) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row.as_dict(), ensure_ascii=True) + "\n")
