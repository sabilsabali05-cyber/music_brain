from __future__ import annotations

from pydantic import BaseModel, Field


class SynplantRoundVariation(BaseModel):
    variation_id: str
    round_id: str
    strategy: str
    verification_passed: bool = False
    fake_usage_detected: bool = False
    source_round_sound_ids: list[str] = Field(default_factory=list)
    output_audio_path: str = ""
    training_allowed: bool = True
    notes: str = ""
