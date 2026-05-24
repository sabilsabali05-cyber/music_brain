from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import re


PROMOTION_LABELS = {"training_safe", "retrieval_only", "excluded"}
AUTHORIZATION_ALLOWED_FOR_TRAINING = {"accepted", "authorized"}
AUTHORIZATION_RETRIEVAL_ONLY = {"copyrighted", "reference", "unknown"}
AUTHORIZATION_EXCLUDED = {"unauthorized", "private", "sensitive"}

PRIVATE_PATH_PATTERNS = [
    re.compile(r"[A-Za-z]:[/\\]Users[/\\][^/\\]+", re.IGNORECASE),
    re.compile(r"/Users/[^/]+", re.IGNORECASE),
]
RAW_URL_PATTERNS = [
    re.compile(r"https?://", re.IGNORECASE),
]


def clamp_score(value: float | int | None) -> float | None:
    if value is None:
        return None
    number = float(value)
    if number < 0.0:
        return 0.0
    if number > 1.0:
        return 1.0
    return number


def _to_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _to_bool(value: Any, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y"}:
            return True
        if lowered in {"false", "0", "no", "n"}:
            return False
    return default


def _redact_path(value: str) -> str:
    redacted = value
    for pattern in PRIVATE_PATH_PATTERNS:
        redacted = pattern.sub("<PRIVATE_LOCAL_PATH>", redacted)
    for pattern in RAW_URL_PATTERNS:
        redacted = pattern.sub("<REDACTED_URL>", redacted)
    return redacted


def _is_redacted_path(value: str) -> bool:
    return value == _redact_path(value)


@dataclass(frozen=True)
class FeatureProvenance:
    source_artifact: str
    source_path_redacted: str
    extractor_name: str
    extractor_version: str
    confidence: float | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_path_redacted", _redact_path(self.source_path_redacted))
        if not _is_redacted_path(self.source_path_redacted):
            raise ValueError("source_path_redacted must not contain private paths or raw URLs")
        if self.confidence is not None:
            object.__setattr__(self, "confidence", clamp_score(self.confidence))

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "FeatureProvenance":
        provenance = row.get("provenance")
        extractor_name = "music_intelligence_schema_v1"
        extractor_version = "1.0.0"
        confidence = None
        if isinstance(provenance, dict):
            extractor_name = str(provenance.get("extractor_name") or extractor_name)
            extractor_version = str(provenance.get("feature_version") or extractor_version)
            confidence = _to_optional_float(provenance.get("confidence"))
        source_path = str(row.get("source_path_redacted", row.get("source_artifact", "")))
        return cls(
            source_artifact=str(row.get("source_artifact", "")),
            source_path_redacted=source_path,
            extractor_name=extractor_name,
            extractor_version=extractor_version,
            confidence=confidence,
            notes=None,
        )


@dataclass(frozen=True)
class ValueMoment:
    start_seconds: float
    end_seconds: float
    start_bar: int | None = None
    start_beat: float | None = None
    end_bar: int | None = None
    end_beat: float | None = None
    value_score: float = 0.5
    reason: str = ""

    def __post_init__(self) -> None:
        if self.start_seconds < 0.0:
            raise ValueError("start_seconds must be >= 0")
        if self.end_seconds < self.start_seconds:
            raise ValueError("end_seconds must be >= start_seconds")
        object.__setattr__(self, "value_score", clamp_score(self.value_score) or 0.0)


@dataclass(frozen=True)
class JunkMoment:
    start_seconds: float
    end_seconds: float
    start_bar: int | None = None
    start_beat: float | None = None
    end_bar: int | None = None
    end_beat: float | None = None
    junk_score: float = 0.5
    reason: str = ""

    def __post_init__(self) -> None:
        if self.start_seconds < 0.0:
            raise ValueError("start_seconds must be >= 0")
        if self.end_seconds < self.start_seconds:
            raise ValueError("end_seconds must be >= start_seconds")
        object.__setattr__(self, "junk_score", clamp_score(self.junk_score) or 0.0)


@dataclass(frozen=True)
class TempoStructureFeatures:
    bpm_estimate: float | None = None
    tempo_stability_score: float | None = None
    structure_clarity_score: float | None = None
    motif_recurrence_score: float | None = None
    section_count: int | None = None
    has_complete_tempo_structure: bool = False

    def __post_init__(self) -> None:
        if self.bpm_estimate is not None and not (20.0 <= self.bpm_estimate <= 320.0):
            raise ValueError("bpm_estimate out of range [20, 320]")
        object.__setattr__(self, "tempo_stability_score", clamp_score(self.tempo_stability_score))
        object.__setattr__(self, "structure_clarity_score", clamp_score(self.structure_clarity_score))
        object.__setattr__(self, "motif_recurrence_score", clamp_score(self.motif_recurrence_score))


@dataclass(frozen=True)
class HarmonyTonalityFeatures:
    harmonic_richness_score: float | None = None
    chord_movement_strength_score: float | None = None
    tonality_confidence_score: float | None = None
    modulation_interest_score: float | None = None
    has_complete_harmony_fields: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "harmonic_richness_score", clamp_score(self.harmonic_richness_score))
        object.__setattr__(self, "chord_movement_strength_score", clamp_score(self.chord_movement_strength_score))
        object.__setattr__(self, "tonality_confidence_score", clamp_score(self.tonality_confidence_score))
        object.__setattr__(self, "modulation_interest_score", clamp_score(self.modulation_interest_score))


@dataclass(frozen=True)
class BassMelodyFeatures:
    bass_motion_clarity_score: float | None = None
    melodic_contour_score: float | None = None
    motif_development_score: float | None = None
    counterpoint_interest_score: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "bass_motion_clarity_score", clamp_score(self.bass_motion_clarity_score))
        object.__setattr__(self, "melodic_contour_score", clamp_score(self.melodic_contour_score))
        object.__setattr__(self, "motif_development_score", clamp_score(self.motif_development_score))
        object.__setattr__(self, "counterpoint_interest_score", clamp_score(self.counterpoint_interest_score))


@dataclass(frozen=True)
class RhythmFeatures:
    groove_stability_score: float | None = None
    rhythmic_complexity_score: float | None = None
    syncopation_interest_score: float | None = None
    timing_confidence_score: float | None = None
    has_complete_rhythm_fields: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "groove_stability_score", clamp_score(self.groove_stability_score))
        object.__setattr__(self, "rhythmic_complexity_score", clamp_score(self.rhythmic_complexity_score))
        object.__setattr__(self, "syncopation_interest_score", clamp_score(self.syncopation_interest_score))
        object.__setattr__(self, "timing_confidence_score", clamp_score(self.timing_confidence_score))


@dataclass(frozen=True)
class TextureInstrumentationFeatures:
    texture_clarity_score: float | None = None
    instrumentation_diversity_score: float | None = None
    arrangement_evolution_score: float | None = None
    mix_noise_penalty: float | None = None
    has_complete_texture_fields: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "texture_clarity_score", clamp_score(self.texture_clarity_score))
        object.__setattr__(self, "instrumentation_diversity_score", clamp_score(self.instrumentation_diversity_score))
        object.__setattr__(self, "arrangement_evolution_score", clamp_score(self.arrangement_evolution_score))
        object.__setattr__(self, "mix_noise_penalty", clamp_score(self.mix_noise_penalty))


@dataclass(frozen=True)
class PolicyOutcome:
    authorization_status: str
    training_allowed: bool
    retrieval_allowed: bool
    policy_fields_complete: bool
    labels_complete: bool
    policy_excluded: bool = False

    def __post_init__(self) -> None:
        status = self.authorization_status.strip().lower()
        object.__setattr__(self, "authorization_status", status)


@dataclass(frozen=True)
class PromotionDecision:
    promotion_label: str
    reason: str
    blockers: list[str] = field(default_factory=list)
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if self.promotion_label not in PROMOTION_LABELS:
            raise ValueError(f"Invalid promotion label: {self.promotion_label}")
        object.__setattr__(self, "confidence", clamp_score(self.confidence) or 0.0)


@dataclass(frozen=True)
class MusicIntelligenceRecord:
    item_id: str
    source_artifact: str
    source_path_redacted: str
    tempo_structure: TempoStructureFeatures
    harmony_tonality: HarmonyTonalityFeatures
    bass_melody: BassMelodyFeatures
    rhythm: RhythmFeatures
    texture_instrumentation: TextureInstrumentationFeatures
    valuable_moments: list[ValueMoment]
    junk_moments: list[JunkMoment]
    transcription_confidence: float | None
    emotional_value_score: float | None
    weirdness_value_score: float | None
    policy_outcome: PolicyOutcome
    provenance: FeatureProvenance

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_path_redacted", _redact_path(self.source_path_redacted))
        if not _is_redacted_path(self.source_path_redacted):
            raise ValueError("source_path_redacted must be redacted")
        object.__setattr__(self, "transcription_confidence", clamp_score(self.transcription_confidence))
        object.__setattr__(self, "emotional_value_score", clamp_score(self.emotional_value_score))
        object.__setattr__(self, "weirdness_value_score", clamp_score(self.weirdness_value_score))

    @classmethod
    def from_normalized_row(cls, row: dict[str, Any]) -> "MusicIntelligenceRecord":
        quality_to_score = lambda key: clamp_score((_to_optional_float(row.get(key)) or 0.0) / 10.0)
        tags = {str(tag).lower() for tag in row.get("tags", []) if isinstance(tag, str)}
        transcription_confidence = _to_optional_float(row.get("transcription_confidence"))
        if transcription_confidence is None:
            human_rating = _to_optional_float(row.get("human_rating"))
            if human_rating is not None:
                transcription_confidence = clamp_score(human_rating / 10.0)

        tempo_structure = TempoStructureFeatures(
            bpm_estimate=None,
            tempo_stability_score=quality_to_score("rhythm_quality"),
            structure_clarity_score=quality_to_score("arrangement_quality"),
            motif_recurrence_score=quality_to_score("musicality_quality"),
            section_count=None,
            has_complete_tempo_structure=_to_optional_float(row.get("rhythm_quality")) is not None
            and _to_optional_float(row.get("arrangement_quality")) is not None,
        )
        harmony_tonality = HarmonyTonalityFeatures(
            harmonic_richness_score=quality_to_score("harmony_quality"),
            chord_movement_strength_score=quality_to_score("harmony_quality"),
            tonality_confidence_score=quality_to_score("harmony_quality"),
            modulation_interest_score=quality_to_score("weirdness_quality"),
            has_complete_harmony_fields=_to_optional_float(row.get("harmony_quality")) is not None,
        )
        bass_melody = BassMelodyFeatures(
            bass_motion_clarity_score=quality_to_score("melody_quality"),
            melodic_contour_score=quality_to_score("melody_quality"),
            motif_development_score=quality_to_score("musicality_quality"),
            counterpoint_interest_score=quality_to_score("arrangement_quality"),
        )
        rhythm = RhythmFeatures(
            groove_stability_score=quality_to_score("rhythm_quality"),
            rhythmic_complexity_score=quality_to_score("rhythm_quality"),
            syncopation_interest_score=quality_to_score("weirdness_quality"),
            timing_confidence_score=quality_to_score("rhythm_quality"),
            has_complete_rhythm_fields=_to_optional_float(row.get("rhythm_quality")) is not None,
        )
        texture = TextureInstrumentationFeatures(
            texture_clarity_score=quality_to_score("texture_quality"),
            instrumentation_diversity_score=quality_to_score("texture_quality"),
            arrangement_evolution_score=quality_to_score("arrangement_quality"),
            mix_noise_penalty=clamp_score(1.0 - (quality_to_score("texture_quality") or 0.0)),
            has_complete_texture_fields=_to_optional_float(row.get("texture_quality")) is not None,
        )

        valuable_moments: list[ValueMoment] = []
        if (quality_to_score("musicality_quality") or 0.0) >= 0.7:
            valuable_moments.append(
                ValueMoment(
                    start_seconds=0.0,
                    end_seconds=30.0,
                    value_score=quality_to_score("musicality_quality") or 0.7,
                    reason="high_musicality_label",
                )
            )

        junk_moments: list[JunkMoment] = []
        excluded_reason = str(row.get("excluded_reason", "")).lower()
        if "noise" in excluded_reason or "junk" in excluded_reason or "silence" in tags:
            junk_moments.append(
                JunkMoment(
                    start_seconds=0.0,
                    end_seconds=30.0,
                    junk_score=0.8,
                    reason="excluded_reason_or_tag_noise",
                )
            )

        policy_outcome = PolicyOutcome(
            authorization_status=str(row.get("authorization_status", "unknown")),
            training_allowed=_to_bool(row.get("training_allowed"), default=False),
            retrieval_allowed=_to_bool(row.get("retrieval_allowed"), default=True),
            policy_fields_complete=str(row.get("policy_status", "missing_fields")).lower() == "complete",
            labels_complete=str(row.get("keep_reject_label", "unlabeled")).lower() != "unlabeled",
            policy_excluded=bool(row.get("policy_excluded", False)),
        )

        return cls(
            item_id=str(row.get("item_id", "")),
            source_artifact=str(row.get("source_artifact", "")),
            source_path_redacted=str(row.get("source_path_redacted", row.get("source_artifact", ""))),
            tempo_structure=tempo_structure,
            harmony_tonality=harmony_tonality,
            bass_melody=bass_melody,
            rhythm=rhythm,
            texture_instrumentation=texture,
            valuable_moments=valuable_moments,
            junk_moments=junk_moments,
            transcription_confidence=transcription_confidence,
            emotional_value_score=clamp_score((_to_optional_float(row.get("emotional_quality")) or 0.0) / 10.0),
            weirdness_value_score=clamp_score((_to_optional_float(row.get("weirdness_quality")) or 0.0) / 10.0),
            policy_outcome=policy_outcome,
            provenance=FeatureProvenance.from_row(row),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "source_artifact": self.source_artifact,
            "source_path_redacted": self.source_path_redacted,
            "tempo_structure": self.tempo_structure.__dict__,
            "harmony_tonality": self.harmony_tonality.__dict__,
            "bass_melody": self.bass_melody.__dict__,
            "rhythm": self.rhythm.__dict__,
            "texture_instrumentation": self.texture_instrumentation.__dict__,
            "valuable_moments": [item.__dict__ for item in self.valuable_moments],
            "junk_moments": [item.__dict__ for item in self.junk_moments],
            "transcription_confidence": self.transcription_confidence,
            "emotional_value_score": self.emotional_value_score,
            "weirdness_value_score": self.weirdness_value_score,
            "policy_outcome": self.policy_outcome.__dict__,
            "provenance": self.provenance.__dict__,
        }
