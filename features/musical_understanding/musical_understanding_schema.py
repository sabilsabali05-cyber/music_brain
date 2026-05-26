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
class CoreGesture:
    gesture_id: str
    musical_intent: str
    evidence: str
    confidence: float
    unknowns: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", clamp01(self.confidence))
        object.__setattr__(self, "unknowns", [str(item) for item in self.unknowns if str(item).strip()])

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MotifMemory:
    motif_id: str
    motif_shape: str
    where_it_returns: list[str]
    how_it_changes: list[str]
    evidence: str
    confidence: float
    unknowns: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", clamp01(self.confidence))
        object.__setattr__(self, "where_it_returns", [str(item) for item in self.where_it_returns if str(item).strip()])
        object.__setattr__(self, "how_it_changes", [str(item) for item in self.how_it_changes if str(item).strip()])
        object.__setattr__(self, "unknowns", [str(item) for item in self.unknowns if str(item).strip()])

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TensionReleaseEvent:
    event_id: str
    setup: str
    release: str
    timeline_hint: str
    evidence: str
    confidence: float
    unknowns: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", clamp01(self.confidence))
        object.__setattr__(self, "unknowns", [str(item) for item in self.unknowns if str(item).strip()])

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GenerativePrinciple:
    principle_id: str
    principle_statement: str
    rationale: str
    apply_next: str
    evidence: str
    confidence: float
    unknowns: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", clamp01(self.confidence))
        object.__setattr__(self, "unknowns", [str(item) for item in self.unknowns if str(item).strip()])

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MusicalUnderstandingDossier:
    dossier_id: str
    source_path_redacted: str
    missing_local_midi_draft: bool
    training_allowed: bool
    heard_evidence_summary: str
    what_is_unknown: list[str]
    core_gestures: list[CoreGesture]
    motif_memory: list[MotifMemory]
    tension_release_map: list[TensionReleaseEvent]
    generative_principles: list[GenerativePrinciple]
    critique_summary: str
    where_it_feels_alive: list[str]
    where_it_feels_generic: list[str]
    what_to_revise_next: list[str]
    top_strengths: list[str] = field(default_factory=list)
    top_weaknesses: list[str] = field(default_factory=list)
    engineering_diagnostics: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    confidence_reason: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_path_redacted", redact_private_path(self.source_path_redacted))
        object.__setattr__(self, "confidence", clamp01(self.confidence))
        object.__setattr__(self, "what_is_unknown", [str(item) for item in self.what_is_unknown if str(item).strip()])

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["core_gestures"] = [item.to_dict() for item in self.core_gestures]
        payload["motif_memory"] = [item.to_dict() for item in self.motif_memory]
        payload["tension_release_map"] = [item.to_dict() for item in self.tension_release_map]
        payload["generative_principles"] = [item.to_dict() for item in self.generative_principles]
        return payload
