from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ModelRole:
    model: str
    role: str
    witness_required: bool
    fallback_behavior: str
    activation_evidence_required: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


MODEL_ROLE_REGISTRY: dict[str, ModelRole] = {
    "basicpitch": ModelRole(
        model="basicpitch",
        role="audio_to_midi_transcription",
        witness_required=True,
        fallback_behavior="skip_transcription_and_mark_clip_untranscribed",
        activation_evidence_required=["smoke_output_midi_exists", "note_count_gt_zero", "real_backend_observation_eq_1"],
    ),
    "demucs": ModelRole(
        model="demucs",
        role="stem_separation",
        witness_required=True,
        fallback_behavior="run_without_stems_and_record_demucs_blocker",
        activation_evidence_required=["readable_stems_gte_2", "real_backend_observation_eq_1"],
    ),
    "moonbeam": ModelRole(
        model="moonbeam",
        role="symbolic_generation",
        witness_required=False,
        fallback_behavior="skip_symbolic_context_generation",
        activation_evidence_required=["generated_symbolic_output_exists", "real_backend_observation_eq_1"],
    ),
    "mt3": ModelRole(
        model="mt3",
        role="audio_to_midi_transcription",
        witness_required=False,
        fallback_behavior="fallback_to_basicpitch_transcription",
        activation_evidence_required=["smoke_output_midi_exists", "real_backend_observation_eq_1"],
    ),
    "omnizart": ModelRole(
        model="omnizart",
        role="audio_to_symbolic_transcription",
        witness_required=False,
        fallback_behavior="fallback_to_active_transcription_backends",
        activation_evidence_required=["smoke_output_generated", "real_backend_observation_eq_1"],
    ),
    "musicbert": ModelRole(
        model="musicbert",
        role="symbolic_analysis",
        witness_required=False,
        fallback_behavior="omit_symbolic_analysis_features_from_ensemble",
        activation_evidence_required=["analysis_artifact_exists", "real_backend_observation_eq_1"],
    ),
    "midigpt": ModelRole(
        model="midigpt",
        role="symbolic_generation",
        witness_required=False,
        fallback_behavior="omit_midigpt_generation_lane",
        activation_evidence_required=["generated_symbolic_output_exists", "real_backend_observation_eq_1"],
    ),
    "text2midi": ModelRole(
        model="text2midi",
        role="text_conditioned_midi_generation",
        witness_required=False,
        fallback_behavior="omit_text_to_midi_lane",
        activation_evidence_required=["generated_symbolic_output_exists", "real_backend_observation_eq_1"],
    ),
}

