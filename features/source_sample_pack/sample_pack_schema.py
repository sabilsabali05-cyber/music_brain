from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class SamplePackCandidate:
    candidate_id: str
    source_id: str
    path_hash: str
    source_redacted_path: str
    role: str
    role_confidence: float
    bar_length: int
    bpm_estimate: float | None
    bpm_estimate_source: str
    key_estimate: str | None
    key_estimate_source: str
    start_seconds: float
    duration_seconds: float | None
    analysis_allowed: bool
    export_allowed: bool
    reference_only: bool
    from_controlled_batch: bool
    witness_ids: list[str] = field(default_factory=list)
    witness_consensus_confidence: float | None = None
    evidence_summary: str = ""
    policy_blockers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SamplePackExport:
    pack_id: str
    generated_at: str
    source_items_considered: int
    loop_candidates_found: int
    audio_loops_exported: int
    midi_starters_created: int
    recipe_starters_created: int
    reference_only_audio_skipped: int
    export_violations: bool
    reaper_bridge_export_supported: bool
    private_paths_detected: bool
    output_folder: str
    manifest_path: str
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
