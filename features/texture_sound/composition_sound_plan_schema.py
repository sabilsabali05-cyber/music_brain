from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

TrackRole = Literal[
    "bass",
    "lead",
    "pad",
    "pluck",
    "percussion",
    "fx",
    "riser",
    "choir_like",
    "texture_bed",
    "drone",
    "counter_melody",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class InstrumentTextureRequest:
    texture_request_id: str
    track_role: TrackRole
    desired_texture_description: str
    priority: int = 0
    constraints: list[str] = field(default_factory=list)


@dataclass
class TrackSoundRole:
    track_id: str
    midi_part_id: str
    track_role: TrackRole
    texture_request_id: str
    notes: str = ""


@dataclass
class SampleSeedAssignment:
    assignment_id: str
    track_id: str
    midi_part_id: str
    track_role: TrackRole
    texture_request_id: str
    sample_search_query_id: str
    seed_sample_id: str
    seed_audio_path: str
    assignment_reason: str = ""


@dataclass
class SynplantPatchAssignment:
    assignment_id: str
    track_id: str
    midi_part_id: str
    track_role: TrackRole
    texture_request_id: str
    seed_sample_id: str
    synplant_session_id: str
    synplant_candidate_id: str
    synplant_patch_ref: str
    rendered_audio_ref: str
    selected_by: Literal["human", "model", "hybrid"] = "human"


@dataclass
class PureDataSystemAssignment:
    assignment_id: str
    track_id: str
    midi_part_id: str
    track_role: TrackRole
    texture_request_id: str
    pd_request_id: str
    pd_candidate_id: str
    pd_template_id: str | None = None
    generated_patch_path: str = ""
    rendered_audio_refs: list[str] = field(default_factory=list)
    selected_by: Literal["human", "model", "hybrid"] = "human"


@dataclass
class MaxForLiveRoutingPlan:
    route_id: str
    ableton_track_name: str
    track_id: str
    midi_part_id: str
    audio_source_ref: str
    max_device_chain: list[str] = field(default_factory=list)
    macro_targets: dict[str, str] = field(default_factory=dict)
    routing_notes: str = ""


@dataclass
class CompositionSoundPlan:
    composition_id: str
    track_sound_roles: list[TrackSoundRole] = field(default_factory=list)
    texture_requests: list[InstrumentTextureRequest] = field(default_factory=list)
    sample_seed_assignments: list[SampleSeedAssignment] = field(default_factory=list)
    synplant_patch_assignments: list[SynplantPatchAssignment] = field(default_factory=list)
    pure_data_system_assignments: list[PureDataSystemAssignment] = field(default_factory=list)
    max_for_live_routing_plan: list[MaxForLiveRoutingPlan] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)
