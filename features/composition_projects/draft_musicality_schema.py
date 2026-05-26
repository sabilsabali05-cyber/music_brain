from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
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


def redact_private_path(value: str) -> str:
    text = str(value).replace("\\", "/")
    text = re.sub(r"[A-Za-z]:/Users/[^/]+/", "<PRIVATE_LOCAL_PATH>/", text)
    text = text.replace("/Users/", "<PRIVATE_LOCAL_PATH>/")
    return text


@dataclass(frozen=True)
class DraftMusicalityAnalysis:
    analysis_id: str
    source_path_redacted: str
    missing_local_midi_draft: bool
    training_allowed: bool
    duration_seconds: float
    tempo_bpm_detected: float | None
    key_detected: str | None
    note_count: int
    track_count: int
    harmony_score: float
    melody_motif_score: float
    rhythm_groove_score: float
    bass_score: float
    structure_score: float
    texture_arrangement_score: float
    musicality_score: float
    top_strengths: list[str] = field(default_factory=list)
    top_weaknesses: list[str] = field(default_factory=list)
    arrangement_roles: list[str] = field(default_factory=list)
    improvement_plan: list[str] = field(default_factory=list)
    recommended_controls: list[str] = field(default_factory=list)
    confidence: float = 0.0
    confidence_reason: str = ""
    technical_summary: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_path_redacted", redact_private_path(self.source_path_redacted))
        object.__setattr__(self, "harmony_score", clamp01(self.harmony_score))
        object.__setattr__(self, "melody_motif_score", clamp01(self.melody_motif_score))
        object.__setattr__(self, "rhythm_groove_score", clamp01(self.rhythm_groove_score))
        object.__setattr__(self, "bass_score", clamp01(self.bass_score))
        object.__setattr__(self, "structure_score", clamp01(self.structure_score))
        object.__setattr__(self, "texture_arrangement_score", clamp01(self.texture_arrangement_score))
        object.__setattr__(self, "musicality_score", clamp01(self.musicality_score))
        object.__setattr__(self, "confidence", clamp01(self.confidence))
        object.__setattr__(self, "duration_seconds", max(0.0, float(self.duration_seconds)))
        object.__setattr__(self, "note_count", max(0, int(self.note_count)))
        object.__setattr__(self, "track_count", max(0, int(self.track_count)))
        object.__setattr__(self, "top_strengths", list(self.top_strengths)[:10])
        object.__setattr__(self, "top_weaknesses", list(self.top_weaknesses)[:10])

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
