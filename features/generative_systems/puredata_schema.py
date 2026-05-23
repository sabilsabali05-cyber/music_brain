from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PureDataPatchTemplate:
    template_id: str
    patch_role: str
    template_patch_ref: str


@dataclass
class PureDataObjectNode:
    node_id: str
    object_type: str


@dataclass
class PureDataConnection:
    source_node_id: str
    target_node_id: str
    connection_type: str


@dataclass
class PureDataParameter:
    parameter_id: str
    parameter_name: str
    value_range: str = ""


@dataclass
class PureDataControlMapping:
    mapping_id: str
    midi_input_ref: str | None = None
    osc_input_ref: str | None = None
    audio_input_ref: str | None = None
    audio_output_ref: str | None = None


@dataclass
class PureDataPatchGraph:
    graph_id: str
    nodes: list[PureDataObjectNode] = field(default_factory=list)
    connections: list[PureDataConnection] = field(default_factory=list)


@dataclass
class PureDataGenerationRequest:
    request_id: str
    patch_role: str
    template_id: str


@dataclass
class PureDataPatchCandidate:
    candidate_id: str
    request_id: str
    patch_ref: str
    limitations: list[str] = field(default_factory=list)


@dataclass
class PureDataRenderResult:
    candidate_id: str
    render_ref: str


@dataclass
class PureDataFeedbackRecord:
    candidate_id: str
    human_rating: float | None = None
    limitations: list[str] = field(default_factory=list)
