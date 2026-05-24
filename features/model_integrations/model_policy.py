from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from features.model_integrations.model_registry import model_registry_by_id


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    tags: list[str]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def training_source_policy(source_name: str, authorization_status: str) -> PolicyDecision:
    source = source_name.strip().lower()
    auth = authorization_status.strip().lower()
    if source == "splice":
        return PolicyDecision(False, "No model trains on Splice.", ["blocked_splice"])
    if auth in {"unknown", "unverified", ""}:
        return PolicyDecision(False, "No model trains on unknown authorization.", ["blocked_unknown_authorization"])
    return PolicyDecision(True, "Source authorized for policy-gated training.", ["authorized_training_source"])


def public_report_path_policy(text: str) -> PolicyDecision:
    if ("C:/" + "Users/") in text or ("C:\\" + "Users\\") in text:
        return PolicyDecision(False, "No model reads private paths into public reports.", ["blocked_private_path_in_public_report"])
    return PolicyDecision(True, "Public report content is path-safe.", ["public_report_path_safe"])


def model_usage_policy(model_id: str) -> PolicyDecision:
    registry = model_registry_by_id()
    record = registry.get(model_id)
    if record is None:
        return PolicyDecision(False, "Unknown model id.", ["unknown_model"])
    if record.family == "audio_generation_reference":
        return PolicyDecision(False, "Audio generation models are reference-only unless explicitly enabled.", ["reference_only"])
    if record.family == "transcription":
        return PolicyDecision(True, "Transcription models are witnesses, not ground truth.", ["witness_not_truth"])
    if record.family == "source_separation":
        return PolicyDecision(True, "Source separation outputs are weak evidence unless reviewed.", ["weak_evidence"])
    if record.family == "symbolic_generation":
        return PolicyDecision(True, "Symbolic generation outputs require human review before training reuse.", ["human_review_required"])
    if model_id in {"synplant_seed_selector", "synplant_patch_ranker"}:
        return PolicyDecision(True, "Synplant outputs inherit seed restrictions.", ["synplant_seed_restrictions"])
    return PolicyDecision(True, "Policy allows read-only integration usage.", ["usage_allowed"])


def can_train_from_feedback(model_id: str) -> PolicyDecision:
    if model_id in {"synplant_seed_selector", "synplant_patch_ranker", "musicbert", "texture_embedding_model"}:
        return PolicyDecision(True, "User feedback can train rankers/preference models.", ["feedback_training_allowed"])
    return PolicyDecision(False, "Feedback training is limited to rankers/preference models.", ["feedback_training_not_allowed"])


def fine_tune_corpus_policy(corpus_validated: bool) -> PolicyDecision:
    if not corpus_validated:
        return PolicyDecision(False, "Fine-tuning requires validated training corpus.", ["blocked_unvalidated_corpus"])
    return PolicyDecision(True, "Validated corpus allows fine-tuning workflow.", ["validated_corpus"])


def transcription_witness_policy_state() -> dict[str, Any]:
    return {
        "yourmt3_available": False,
        "basic_pitch_available": False,
        "transcription_performed": False,
        "model_training_has_occurred": False,
        "witness_policy": "witness_not_truth",
    }


def source_separation_witness_policy_state() -> dict[str, Any]:
    return {
        "demucs_available": False,
        "source_separation_performed": False,
        "stems_generated": False,
        "downloads_performed": False,
        "model_training_has_occurred": False,
        "witness_policy": "weak_evidence_not_truth",
        "training_use_allowed": "false_by_default",
    }
