from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class ChordPotionPresetProfile:
    preset_id: str
    display_name: str
    local_preset_name: str
    category: str
    expected_pattern_family: str
    expected_density: float
    expected_syncopation: float
    expected_motion: float
    expected_register_behavior: str
    expected_texture: str
    known_good_for: list[str] = field(default_factory=list)
    known_bad_for: list[str] = field(default_factory=list)
    user_rating: float = 0.0
    audition_count: int = 0
    avg_score: float = 0.0
    notes: str = ""

    def as_prior_dict(self) -> dict:
        payload = asdict(self)
        payload["notes"] = (self.notes + " (prior expectation, must be validated by audition output)").strip()
        return payload


def load_preset_profiles_from_vst_registry(path: Path, plugin_id: str) -> list[ChordPotionPresetProfile]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []
    plugins = payload.get("plugins", []) if isinstance(payload, dict) else []
    for plugin in plugins:
        if not isinstance(plugin, dict):
            continue
        if str(plugin.get("plugin_id", "")).strip() != plugin_id:
            continue
        profiles = plugin.get("preset_profiles", [])
        if not isinstance(profiles, list):
            return []
        parsed: list[ChordPotionPresetProfile] = []
        for item in profiles:
            if not isinstance(item, dict):
                continue
            parsed.append(
                ChordPotionPresetProfile(
                    preset_id=str(item.get("preset_id", "")).strip(),
                    display_name=str(item.get("display_name", "")).strip(),
                    local_preset_name=str(item.get("local_preset_name", "")).strip(),
                    category=str(item.get("category", "general")).strip() or "general",
                    expected_pattern_family=str(item.get("expected_pattern_family", "minimal_support_pattern")).strip(),
                    expected_density=float(item.get("expected_density", 0.5) or 0.0),
                    expected_syncopation=float(item.get("expected_syncopation", 0.5) or 0.0),
                    expected_motion=float(item.get("expected_motion", 0.5) or 0.0),
                    expected_register_behavior=str(item.get("expected_register_behavior", "mid_support")).strip(),
                    expected_texture=str(item.get("expected_texture", "neutral")).strip(),
                    known_good_for=[str(x).strip() for x in item.get("known_good_for", []) if str(x).strip()],
                    known_bad_for=[str(x).strip() for x in item.get("known_bad_for", []) if str(x).strip()],
                    user_rating=float(item.get("user_rating", 0.0) or 0.0),
                    audition_count=int(item.get("audition_count", 0) or 0),
                    avg_score=float(item.get("avg_score", 0.0) or 0.0),
                    notes=str(item.get("notes", "")).strip(),
                )
            )
        return [profile for profile in parsed if profile.preset_id]
    return []


def write_prior_registry(path: Path, profiles: list[ChordPotionPresetProfile]) -> None:
    payload = {
        "registry_type": "chordpotion_preset_prior_registry",
        "interpretation": "priors_not_truth",
        "preset_profiles": [item.as_prior_dict() for item in profiles],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
