from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

PureDataPatchRole = Literal[
    "euclidean_rhythm_generator",
    "probability_drum_machine",
    "markov_melody_generator",
    "granular_texture",
    "drone_generator",
    "chaos_modulation",
    "spectral_freeze_effect",
    "live_audio_processor",
    "midi_transformer",
    "control_signal_generator",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class PureDataParameter:
    parameter_id: str
    name: str
    value_type: Literal["float", "int", "bool", "enum", "trigger"]
    default_value: Any = None
    min_value: float | None = None
    max_value: float | None = None
    unit: str = ""
    description: str = ""


@dataclass
class PureDataObjectNode:
    node_id: str
    object_name: str
    object_category: Literal["midi", "osc", "audio", "math", "random", "sequencer", "effect", "control", "utility"]
    inlets: int = 0
    outlets: int = 0
    parameters: list[PureDataParameter] = field(default_factory=list)
    notes: str = ""


@dataclass
class PureDataConnection:
    source_node_id: str
    source_outlet_index: int
    target_node_id: str
    target_inlet_index: int
    connection_type: Literal["audio", "control", "midi", "osc"] = "control"


@dataclass
class PureDataPatchGraph:
    graph_id: str
    nodes: list[PureDataObjectNode] = field(default_factory=list)
    connections: list[PureDataConnection] = field(default_factory=list)
    midi_inputs: list[str] = field(default_factory=list)
    osc_inputs: list[str] = field(default_factory=list)
    audio_inputs: list[str] = field(default_factory=list)
    audio_outputs: list[str] = field(default_factory=list)
    random_sources: list[str] = field(default_factory=list)
    sequencer_or_generator_type: str = ""
    synthesis_or_effect_type: str = ""
    object_graph_summary: str = ""


@dataclass
class PureDataPatchTemplate:
    template_id: str
    display_name: str
    patch_role: PureDataPatchRole
    template_patch_path: str
    graph: PureDataPatchGraph
    parameter_ranges: dict[str, dict[str, float | int | str]] = field(default_factory=dict)
    song_section_triggers: list[str] = field(default_factory=list)
    usage_notes: str = ""


@dataclass
class PureDataControlMapping:
    mapping_id: str
    source: Literal["midi", "osc", "max_for_live", "ableton_automation", "manual"]
    source_ref: str
    target_parameter_id: str
    transform: str = "identity"
    min_output: float | None = None
    max_output: float | None = None


@dataclass
class PureDataGenerationRequest:
    request_id: str
    composition_id: str
    track_role: str
    patch_role: PureDataPatchRole
    requested_texture_description: str
    template_id: str | None = None
    seed_notes: list[str] = field(default_factory=list)
    control_mappings: list[PureDataControlMapping] = field(default_factory=list)
    max_ableton_routing_refs: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


@dataclass
class PureDataPatchCandidate:
    candidate_id: str
    request_id: str
    composition_id: str
    track_role: str
    patch_role: PureDataPatchRole
    template_id: str | None = None
    generated_patch_path: str = ""
    graph_summary: PureDataPatchGraph = field(default_factory=lambda: PureDataPatchGraph(graph_id=""))
    control_mappings: list[PureDataControlMapping] = field(default_factory=list)
    max_ableton_routing_refs: list[str] = field(default_factory=list)
    human_rating: float | None = None
    model_rating: float | None = None
    selected: bool = False
    selection_reason: str = ""
    limitations: list[str] = field(default_factory=list)


@dataclass
class PureDataRenderResult:
    candidate_id: str
    request_id: str
    composition_id: str
    rendered_audio_refs: list[str] = field(default_factory=list)
    max_ableton_routing_refs: list[str] = field(default_factory=list)
    render_notes: str = ""
    rendered_at: str = field(default_factory=now_iso)


@dataclass
class PureDataFeedbackRecord:
    candidate_id: str
    request_id: str
    composition_id: str
    selected: bool
    human_rating: float | None = None
    model_rating: float | None = None
    fit_to_role_score: float | None = None
    fit_to_mix_score: float | None = None
    novelty_score: float | None = None
    comments: str = ""
    created_at: str = field(default_factory=now_iso)
