from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TrackSoundRole:
    midi_part_id: str
    instrument_role: str


@dataclass
class InstrumentTextureRequest:
    texture_request_id: str
    requested_texture: str


@dataclass
class SampleSeedAssignment:
    texture_request_id: str
    sample_seed_id: str


@dataclass
class SynplantPatchAssignment:
    texture_request_id: str
    synplant_patch_ref: str


@dataclass
class PureDataSystemAssignment:
    texture_request_id: str
    pure_data_patch_ref: str


@dataclass
class MaxForLiveRoutingPlan:
    track_id: str
    routing_ref: str


@dataclass
class CompositionSoundPlan:
    composition_id: str
    track_sound_roles: list[TrackSoundRole] = field(default_factory=list)
    texture_requests: list[InstrumentTextureRequest] = field(default_factory=list)
    sample_seed_assignments: list[SampleSeedAssignment] = field(default_factory=list)
    synplant_patch_assignments: list[SynplantPatchAssignment] = field(default_factory=list)
    pure_data_system_assignments: list[PureDataSystemAssignment] = field(default_factory=list)
    max_for_live_routing_plan: list[MaxForLiveRoutingPlan] = field(default_factory=list)
