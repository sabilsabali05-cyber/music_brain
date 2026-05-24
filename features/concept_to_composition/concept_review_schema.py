from __future__ import annotations

from pydantic import BaseModel, Field


class CandidateEvaluation(BaseModel):
    candidate_name: str
    concept_alignment_score: float = Field(ge=0.0, le=1.0)
    emotional_arc_score: float = Field(ge=0.0, le=1.0)
    harmony_score: float = Field(ge=0.0, le=1.0)
    voice_leading_score: float = Field(ge=0.0, le=1.0)
    rhythm_identity_score: float = Field(ge=0.0, le=1.0)
    texture_intent_score: float = Field(ge=0.0, le=1.0)
    random_note_penalty: float = Field(ge=0.0, le=1.0)
    clutter_penalty: float = Field(ge=0.0, le=1.0)
    weirdness_musicality_score: float = Field(ge=0.0, le=1.0)
    midi_parse_success: bool


class ConceptGenerationEvaluation(BaseModel):
    concept_id: str
    best_candidate: str
    candidates: list[CandidateEvaluation]
    summary: str
