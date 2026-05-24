from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ArrangementSection:
    section_id: str
    label: str
    start_bar: int
    end_bar: int


@dataclass
class TrackState:
    track_id: str
    track_name: str
    track_type: str
    volume: float = 0.8
    pan: float = 0.0
    grouped_under: str | None = None


@dataclass
class ClipState:
    clip_id: str
    track_id: str
    section_id: str
    start_bar: int
    end_bar: int
    clip_kind: str = "midi"


@dataclass
class DeviceState:
    device_id: str
    track_id: str
    device_name: str
    parameters: list[str] = field(default_factory=list)


@dataclass
class AbletonProjectState:
    tempo: float
    time_signature: str
    arrangement_sections: list[ArrangementSection] = field(default_factory=list)
    tracks: list[TrackState] = field(default_factory=list)
    clips: list[ClipState] = field(default_factory=list)
    devices: list[DeviceState] = field(default_factory=list)
    parameters: list[str] = field(default_factory=list)
    automation_lanes: list[str] = field(default_factory=list)
    markers: list[str] = field(default_factory=list)
    key_harmony_estimate: str = "unknown"
    density_estimate: str = "unknown"
    available_generated_candidates: list[dict[str, Any]] = field(default_factory=list)
    human_review_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tempo": self.tempo,
            "time_signature": self.time_signature,
            "arrangement_sections": [section.__dict__ for section in self.arrangement_sections],
            "tracks": [track.__dict__ for track in self.tracks],
            "clips": [clip.__dict__ for clip in self.clips],
            "devices": [device.__dict__ for device in self.devices],
            "parameters": list(self.parameters),
            "automation_lanes": list(self.automation_lanes),
            "markers": list(self.markers),
            "key_harmony_estimate": self.key_harmony_estimate,
            "density_estimate": self.density_estimate,
            "available_generated_candidates": list(self.available_generated_candidates),
            "human_review_notes": list(self.human_review_notes),
        }
