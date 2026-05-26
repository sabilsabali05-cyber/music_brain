from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class LoopRole(str, Enum):
    FULL = "full"
    BASS = "bass"
    CHORDS = "chords"
    LEAD = "lead"
    TEXTURE = "texture"
    DRUMS = "drums"
    PERCUSSION = "percussion"


class RendererKind(str, Enum):
    CONFIGURED_LOCAL = "configured_local_renderer"
    SOUNDFONT = "soundfont_renderer"
    PYTHON_PREVIEW = "python_preview_synth"


class RenderQualityTier(str, Enum):
    HIGH = "high_quality"
    PREVIEW = "preview_quality"


@dataclass(frozen=True)
class LoopPair:
    pair_id: str
    pack_id: str
    basename: str
    role: LoopRole
    midi_path: str
    audio_path: str
    pair_metadata_path: str
    tempo_bpm: float
    key_hint: str
    bars: int
    beats_per_bar: int
    duration_seconds: float
    renderer_used: RendererKind
    render_quality: RenderQualityTier
    render_verified: bool
    preview_limited: bool
    source_midi_path: str
    source_stem_path: str
    source_principles: list[str] = field(default_factory=list)
    role_use_principles: list[str] = field(default_factory=list)
    draft_gesture_influence: str = ""
    quality_notes: list[str] = field(default_factory=list)
    evidence_limits: list[str] = field(default_factory=list)
    usage_notes: list[str] = field(default_factory=list)
    no_private_paths_detected: bool = True
    source_taste_dossier_used: bool = False
    witness_consensus_used: bool = False
    draft_understanding_used: bool = False
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LoopPackManifest:
    pack_id: str
    created_at: str
    pack_path: str
    input_midi_path: str
    stem_dir_path: str
    midi_loop_count: int
    audio_loop_count: int
    paired_loop_count: int
    audio_orphan_count: int
    renderer_used: RendererKind
    render_verified_count: int
    pack_verified: bool
    private_paths_detected: bool
    source_taste_dossier_used: bool
    witness_consensus_used: bool
    draft_understanding_used: bool
    strongest_loops: list[str] = field(default_factory=list)
    weakest_evidence_limits: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    loops: list[LoopPair] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "loops": [loop.to_dict() for loop in self.loops],
        }
