from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path


class ChordPotionTargetPatternFamily(str, Enum):
    SPARSE_EMOTIONAL_PULSE = "sparse_emotional_pulse"
    ROLLING_CHORD_MOTION = "rolling_chord_motion"
    BROKEN_CHORD_PIANO = "broken_chord_piano"
    ARPEGGIATED_PAD_MOTION = "arpeggiated_pad_motion"
    SYNCOPATED_CHORD_STABS = "syncopated_chord_stabs"
    GOSPEL_LIKE_PULSE = "gospel_like_pulse"
    RAP_POCKET_CHOPS = "rap_pocket_chops"
    AMBIENT_SLOW_MOTION = "ambient_slow_motion"
    DENSE_EXPERIMENTAL_PATTERN = "dense_experimental_pattern"
    TENSION_BUILD_PATTERN = "tension_build_pattern"
    MINIMAL_SUPPORT_PATTERN = "minimal_support_pattern"


@dataclass
class ChordPotionTargetIntent:
    intent_id: str
    source_generation_id: str
    target_role: str
    source_chord_skeleton: str
    target_pattern_family: ChordPotionTargetPatternFamily
    target_density: float
    target_syncopation: float
    target_motion: float
    target_repetition: float
    target_variation: float
    target_humanization: float
    target_register_behavior: str
    preserve_bass: bool
    preserve_top_voice: bool
    preserve_harmonic_rhythm: bool
    preserve_chord_identity: bool
    avoid_mud: bool
    avoid_random_keyboard_effect: bool
    avoid_overbusy_output: bool
    avoid_lead_conflict: bool
    desired_ear_effect: str
    texture_profile: str
    theory_profile: str
    confidence: float

    def as_dict(self) -> dict:
        payload = asdict(self)
        payload["target_pattern_family"] = self.target_pattern_family.value
        return payload


def write_target_intent(path: Path, intent: ChordPotionTargetIntent) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(intent.as_dict(), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def load_target_intent(path: Path) -> ChordPotionTargetIntent:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ChordPotionTargetIntent(
        intent_id=str(payload.get("intent_id", "")),
        source_generation_id=str(payload.get("source_generation_id", "")),
        target_role=str(payload.get("target_role", "")),
        source_chord_skeleton=str(payload.get("source_chord_skeleton", "")),
        target_pattern_family=ChordPotionTargetPatternFamily(
            str(payload.get("target_pattern_family", ChordPotionTargetPatternFamily.MINIMAL_SUPPORT_PATTERN.value))
        ),
        target_density=float(payload.get("target_density", 0.5) or 0.0),
        target_syncopation=float(payload.get("target_syncopation", 0.5) or 0.0),
        target_motion=float(payload.get("target_motion", 0.5) or 0.0),
        target_repetition=float(payload.get("target_repetition", 0.5) or 0.0),
        target_variation=float(payload.get("target_variation", 0.5) or 0.0),
        target_humanization=float(payload.get("target_humanization", 0.5) or 0.0),
        target_register_behavior=str(payload.get("target_register_behavior", "supportive_mid_register")),
        preserve_bass=bool(payload.get("preserve_bass", True)),
        preserve_top_voice=bool(payload.get("preserve_top_voice", True)),
        preserve_harmonic_rhythm=bool(payload.get("preserve_harmonic_rhythm", True)),
        preserve_chord_identity=bool(payload.get("preserve_chord_identity", True)),
        avoid_mud=bool(payload.get("avoid_mud", True)),
        avoid_random_keyboard_effect=bool(payload.get("avoid_random_keyboard_effect", True)),
        avoid_overbusy_output=bool(payload.get("avoid_overbusy_output", True)),
        avoid_lead_conflict=bool(payload.get("avoid_lead_conflict", True)),
        desired_ear_effect=str(payload.get("desired_ear_effect", "")),
        texture_profile=str(payload.get("texture_profile", "")),
        theory_profile=str(payload.get("theory_profile", "")),
        confidence=float(payload.get("confidence", 0.5) or 0.0),
    )
