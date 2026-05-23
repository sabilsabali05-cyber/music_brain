from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

AbletonTrackType = Literal["midi", "audio", "synplant_seed", "puredata_placeholder", "max_for_live_placeholder"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AbletonMidiClipAssignment:
    track_name: str
    role: str
    midi_file: str
    arrangement_start_seconds: float
    arrangement_end_seconds: float
    section_name: str
    notes: str = ""
    limitations: str = ""


@dataclass
class AbletonSampleAssignment:
    track_name: str
    role: str
    selected_sample_ref: str
    local_source_path_private: str
    public_safe_sample_label: str
    device_suggestion: str
    notes: str = ""
    limitations: str = "Manual drag-in only; no automatic sample import."


@dataclass
class AbletonSynplantSeedInstruction:
    track_name: str
    role: str
    selected_sample_ref: str
    local_source_path_private: str
    public_safe_sample_label: str
    device_suggestion: str
    notes: str = "Manually drag this sample into Synplant / Ableton if desired."
    limitations: str = "Synplant automation not implemented."


@dataclass
class AbletonPureDataPlaceholder:
    track_name: str
    role: str
    device_suggestion: str
    notes: str
    limitations: str = "Pure Data patch generation/control not implemented in export v1."


@dataclass
class AbletonTrackExportPlan:
    track_name: str
    role: str
    track_type: AbletonTrackType
    midi_file: str = ""
    selected_sample_ref: str = ""
    local_source_path_private: str = ""
    public_safe_sample_label: str = ""
    device_suggestion: str = ""
    notes: str = ""
    arrangement_start_seconds: float = 0.0
    arrangement_end_seconds: float = 0.0
    section_name: str = ""
    limitations: str = ""


@dataclass
class AbletonProjectExportPlan:
    project_name: str
    source_tangible_output: str
    export_root: str
    als_generation_status: Literal["not_implemented_experimental_future"] = "not_implemented_experimental_future"
    tracks: list[AbletonTrackExportPlan] = field(default_factory=list)
    midi_clip_assignments: list[AbletonMidiClipAssignment] = field(default_factory=list)
    sample_assignments: list[AbletonSampleAssignment] = field(default_factory=list)
    synplant_seed_instructions: list[AbletonSynplantSeedInstruction] = field(default_factory=list)
    puredata_placeholders: list[AbletonPureDataPlaceholder] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)


@dataclass
class AbletonExportReport:
    status: str
    export_project_path: str
    midi_files_copied: list[str] = field(default_factory=list)
    public_safe_files_created: list[str] = field(default_factory=list)
    private_files_created: list[str] = field(default_factory=list)
    copied_audio_sample_count: int = 0
    copy_local_samples_enabled: bool = False
    als_generation_status: Literal["not_implemented_experimental_future"] = "not_implemented_experimental_future"
    limitations: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)
