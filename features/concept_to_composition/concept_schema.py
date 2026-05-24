from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TempoRange(BaseModel):
    min_bpm: int = Field(ge=40, le=220)
    max_bpm: int = Field(ge=40, le=220)


class SectionPlanItem(BaseModel):
    name: str
    bars: int = Field(ge=2, le=64)
    intent: str


class SongConceptBrief(BaseModel):
    title: str
    short_description: str
    emotional_core: str
    narrative_arc: str
    perspective: str
    scene_or_image: str
    energy_curve: list[float] = Field(min_length=3, max_length=12)
    tension_curve: list[float] = Field(min_length=3, max_length=12)
    density_curve: list[float] = Field(min_length=3, max_length=12)
    tempo_range: TempoRange
    key_or_mode_preference: str
    harmony_strategy: str
    chord_movement_strategy: str
    bass_strategy: str
    melody_strategy: str
    rhythm_strategy: str
    texture_strategy: str
    arrangement_strategy: str
    section_plan: list[SectionPlanItem] = Field(min_length=3, max_length=12)
    motifs_to_try: list[str] = Field(default_factory=list)
    avoid_patterns: list[str] = Field(default_factory=list)
    preserve_patterns: list[str] = Field(default_factory=list)
    weirdness_policy: str
    vocal_space_policy: str
    reference_influence_policy: str
    generation_seed: int = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0)
    unresolved_questions: list[str] = Field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [
            "# Song Concept Brief",
            "",
            f"- title: {self.title}",
            f"- short_description: {self.short_description}",
            f"- emotional_core: {self.emotional_core}",
            f"- narrative_arc: {self.narrative_arc}",
            f"- perspective: {self.perspective}",
            f"- scene_or_image: {self.scene_or_image}",
            f"- energy_curve: {self.energy_curve}",
            f"- tension_curve: {self.tension_curve}",
            f"- density_curve: {self.density_curve}",
            f"- tempo_range: {self.tempo_range.model_dump()}",
            f"- key_or_mode_preference: {self.key_or_mode_preference}",
            f"- harmony_strategy: {self.harmony_strategy}",
            f"- chord_movement_strategy: {self.chord_movement_strategy}",
            f"- bass_strategy: {self.bass_strategy}",
            f"- melody_strategy: {self.melody_strategy}",
            f"- rhythm_strategy: {self.rhythm_strategy}",
            f"- texture_strategy: {self.texture_strategy}",
            f"- arrangement_strategy: {self.arrangement_strategy}",
            "- section_plan:",
        ]
        for section in self.section_plan:
            lines.append(f"  - {section.name} ({section.bars} bars): {section.intent}")
        lines.extend(
            [
                f"- motifs_to_try: {self.motifs_to_try}",
                f"- avoid_patterns: {self.avoid_patterns}",
                f"- preserve_patterns: {self.preserve_patterns}",
                f"- weirdness_policy: {self.weirdness_policy}",
                f"- vocal_space_policy: {self.vocal_space_policy}",
                f"- reference_influence_policy: {self.reference_influence_policy}",
                f"- generation_seed: {self.generation_seed}",
                f"- confidence: {self.confidence:.2f}",
                f"- unresolved_questions: {self.unresolved_questions}",
                "",
            ]
        )
        return "\n".join(lines)


CandidateName = Literal[
    "candidate_01_harmony_first",
    "candidate_02_rhythm_first",
    "candidate_03_weird_but_musical",
]
