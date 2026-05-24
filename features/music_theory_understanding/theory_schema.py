from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def clamp01(value: float | int | None) -> float:
    if value is None:
        return 0.0
    out = float(value)
    if out < 0.0:
        return 0.0
    if out > 1.0:
        return 1.0
    return out


def _redact_private_path(value: str) -> str:
    return (
        value.replace("C:/Users/", "<PRIVATE_LOCAL_PATH>/")
        .replace("C:\\Users\\", "<PRIVATE_LOCAL_PATH>\\")
        .replace("/Users/", "<PRIVATE_LOCAL_PATH>/")
    )


@dataclass(frozen=True)
class FrameworkApplicability:
    framework: str
    applicable: bool
    not_applicable: bool
    confidence: float
    reasons: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", clamp01(self.confidence))
        if self.not_applicable:
            object.__setattr__(self, "applicable", False)
        if self.applicable:
            object.__setattr__(self, "not_applicable", False)


@dataclass(frozen=True)
class HarmonyUnderstanding:
    not_applicable: bool
    center_hint: str | None
    movement_description: str | None
    color_tones: list[str]
    valuable_weirdness: bool
    random_clash_risk: bool
    confidence: float
    applicability_by_framework: list[FrameworkApplicability] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", clamp01(self.confidence))


@dataclass(frozen=True)
class VoiceLeadingUnderstanding:
    not_applicable: bool
    stepwise_motion_ratio: float
    leap_ratio: float
    likely_parallel_risk: float
    bass_support_quality: float
    confidence: float
    applicability_by_framework: list[FrameworkApplicability] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "stepwise_motion_ratio", clamp01(self.stepwise_motion_ratio))
        object.__setattr__(self, "leap_ratio", clamp01(self.leap_ratio))
        object.__setattr__(self, "likely_parallel_risk", clamp01(self.likely_parallel_risk))
        object.__setattr__(self, "bass_support_quality", clamp01(self.bass_support_quality))
        object.__setattr__(self, "confidence", clamp01(self.confidence))


@dataclass(frozen=True)
class MotifUnderstanding:
    not_applicable: bool
    motif_cell_detected: bool
    recurrence_density: float
    transformability: float
    confidence: float
    applicability_by_framework: list[FrameworkApplicability] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "recurrence_density", clamp01(self.recurrence_density))
        object.__setattr__(self, "transformability", clamp01(self.transformability))
        object.__setattr__(self, "confidence", clamp01(self.confidence))


@dataclass(frozen=True)
class RhythmGrooveUnderstanding:
    not_applicable: bool
    pulse_clarity: float
    syncopation_hint: float
    groove_pocket_value: float
    loop_friendliness: float
    confidence: float
    applicability_by_framework: list[FrameworkApplicability] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "pulse_clarity", clamp01(self.pulse_clarity))
        object.__setattr__(self, "syncopation_hint", clamp01(self.syncopation_hint))
        object.__setattr__(self, "groove_pocket_value", clamp01(self.groove_pocket_value))
        object.__setattr__(self, "loop_friendliness", clamp01(self.loop_friendliness))
        object.__setattr__(self, "confidence", clamp01(self.confidence))


@dataclass(frozen=True)
class FormUnderstanding:
    not_applicable: bool
    section_count_hint: int
    through_composed_tendency: float
    loop_tendency: float
    development_strength: float
    confidence: float
    applicability_by_framework: list[FrameworkApplicability] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "section_count_hint", max(1, int(self.section_count_hint)))
        object.__setattr__(self, "through_composed_tendency", clamp01(self.through_composed_tendency))
        object.__setattr__(self, "loop_tendency", clamp01(self.loop_tendency))
        object.__setattr__(self, "development_strength", clamp01(self.development_strength))
        object.__setattr__(self, "confidence", clamp01(self.confidence))


@dataclass(frozen=True)
class TextureRoleUnderstanding:
    not_applicable: bool
    density_level: float
    layer_separation: float
    atmosphere_weight: float
    lead_presence: float
    confidence: float
    applicability_by_framework: list[FrameworkApplicability] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "density_level", clamp01(self.density_level))
        object.__setattr__(self, "layer_separation", clamp01(self.layer_separation))
        object.__setattr__(self, "atmosphere_weight", clamp01(self.atmosphere_weight))
        object.__setattr__(self, "lead_presence", clamp01(self.lead_presence))
        object.__setattr__(self, "confidence", clamp01(self.confidence))


@dataclass(frozen=True)
class GenerationHooks:
    target_tempo_range: list[int]
    target_key_or_mode: str
    chord_movement_strategy: str
    bass_motion_strategy: str
    voice_leading_strategy: str
    motif_development_strategy: str
    rhythm_strategy: str
    form_strategy: str
    texture_strategy: str
    avoid_list: list[str] = field(default_factory=list)
    preserve_list: list[str] = field(default_factory=list)
    tension_curve: list[float] = field(default_factory=list)
    density_curve: list[float] = field(default_factory=list)
    confidence: float = 0.0
    source_records_used: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        low = int(self.target_tempo_range[0]) if self.target_tempo_range else 60
        high = int(self.target_tempo_range[1]) if len(self.target_tempo_range) > 1 else low + 10
        if low > high:
            low, high = high, low
        object.__setattr__(self, "target_tempo_range", [max(30, low), min(260, high)])
        object.__setattr__(self, "confidence", clamp01(self.confidence))
        object.__setattr__(self, "tension_curve", [clamp01(v) for v in self.tension_curve[:8]])
        object.__setattr__(self, "density_curve", [clamp01(v) for v in self.density_curve[:8]])


@dataclass(frozen=True)
class MusicTheoryUnderstandingRecord:
    item_id: str
    source_artifact: str
    source_path_redacted: str
    authorization_status: str
    training_allowed: bool
    retrieval_allowed: bool
    transcription_reliability_score: float
    generation_usefulness_score: float
    harmonic_interest_score: float
    chord_movement_score: float
    voice_leading_score: float
    motif_reusability_score: float
    rhythm_identity_score: float
    groove_value_score: float
    form_development_score: float
    texture_value_score: float
    clutter_penalty: float
    random_note_penalty: float
    harmony_understanding: HarmonyUnderstanding
    voice_leading_understanding: VoiceLeadingUnderstanding
    motif_understanding: MotifUnderstanding
    rhythm_understanding: RhythmGrooveUnderstanding
    form_understanding: FormUnderstanding
    texture_role_understanding: TextureRoleUnderstanding
    generation_hooks: GenerationHooks
    blocked_by_policy: bool = False
    blocked_by_confidence: bool = False
    theory_notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_path_redacted", _redact_private_path(self.source_path_redacted))
        object.__setattr__(self, "transcription_reliability_score", clamp01(self.transcription_reliability_score))
        object.__setattr__(self, "generation_usefulness_score", clamp01(self.generation_usefulness_score))
        object.__setattr__(self, "harmonic_interest_score", clamp01(self.harmonic_interest_score))
        object.__setattr__(self, "chord_movement_score", clamp01(self.chord_movement_score))
        object.__setattr__(self, "voice_leading_score", clamp01(self.voice_leading_score))
        object.__setattr__(self, "motif_reusability_score", clamp01(self.motif_reusability_score))
        object.__setattr__(self, "rhythm_identity_score", clamp01(self.rhythm_identity_score))
        object.__setattr__(self, "groove_value_score", clamp01(self.groove_value_score))
        object.__setattr__(self, "form_development_score", clamp01(self.form_development_score))
        object.__setattr__(self, "texture_value_score", clamp01(self.texture_value_score))
        object.__setattr__(self, "clutter_penalty", clamp01(self.clutter_penalty))
        object.__setattr__(self, "random_note_penalty", clamp01(self.random_note_penalty))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
