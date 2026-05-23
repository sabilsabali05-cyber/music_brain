from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

TrackRole = Literal["drums", "bass", "chords", "lead", "counter_melody", "texture_bed", "transition_fx"]
GenerationMethod = Literal[
    "example_retrieval",
    "transformed_example",
    "recombined_example",
    "ratio_conditioned_structure",
    "manual_review_required",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class DemoSection:
    section_id: str
    section_name: str
    start_seconds: float
    end_seconds: float
    section_goal: str


@dataclass
class DemoMidiPart:
    part_id: str
    track_role: TrackRole
    source_example_ids: list[str] = field(default_factory=list)
    transformations_applied: list[str] = field(default_factory=list)
    note_count: int = 0


@dataclass
class DemoSoundRole:
    track_role: TrackRole
    requested_texture: str
    generation_method: GenerationMethod


@dataclass
class DemoSynplantSeedSuggestion:
    track_role: TrackRole
    requested_texture: str
    sample_id: str
    source_path: str
    asset_type_guess: str
    reason: str
    training_allowed_assumption: str
    requires_human_review: bool
    note: str = "Use manually in Synplant; no automation performed."


@dataclass
class DemoCompositionPlan:
    plan_id: str
    duration_seconds: float
    structure_ratio: str
    goal: str
    climax_seconds: float
    sections: list[DemoSection] = field(default_factory=list)
    midi_parts: list[DemoMidiPart] = field(default_factory=list)
    sound_roles: list[DemoSoundRole] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)


@dataclass
class DemoGenerationReport:
    status: str
    output_dir: str
    source_dataset_folders: list[str] = field(default_factory=list)
    source_example_ids: list[str] = field(default_factory=list)
    transformations_applied: list[str] = field(default_factory=list)
    prototype_generated_from_existing_examples: bool = True
    not_model_trained: bool = True
    not_ground_truth: bool = True
    not_final_mix: bool = True
    needs_human_review: bool = True
    created_at: str = field(default_factory=now_iso)
