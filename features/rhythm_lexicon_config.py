from __future__ import annotations

from typing import Any


DEFAULT_LEXICON_THRESHOLD: dict[str, Any] = {
    "minimum_confidence": 0.45,
    "strong_confidence": 0.82,
    "moderate_confidence": 0.60,
    "minimum_specificity_score": 0.30,
    "maximum_ambiguity_score": 0.75,
    "required_evidence_fields": ["token_similarity"],
    "negative_control_penalties": {
        "all_onset": 0.45,
        "low_information": 0.65,
        "insufficient_repetition": 0.85,
    },
}


RHYTHM_LEXICON_THRESHOLDS: dict[str, dict[str, Any]] = {
    "tresillo_3_3_2": {
        "minimum_confidence": 0.55,
        "strong_confidence": 0.86,
        "moderate_confidence": 0.66,
        "minimum_specificity_score": 0.42,
        "maximum_ambiguity_score": 0.55,
        "required_evidence_fields": ["token_similarity"],
    },
    "clave": {
        "minimum_confidence": 0.58,
        "strong_confidence": 0.88,
        "moderate_confidence": 0.70,
        "minimum_specificity_score": 0.45,
        "maximum_ambiguity_score": 0.5,
        "required_evidence_fields": ["token_similarity"],
    },
    "cinquillo": {
        "minimum_confidence": 0.55,
        "strong_confidence": 0.86,
        "moderate_confidence": 0.68,
        "minimum_specificity_score": 0.4,
        "maximum_ambiguity_score": 0.58,
    },
    "shuffle": {
        "minimum_confidence": 0.50,
        "strong_confidence": 0.84,
        "moderate_confidence": 0.66,
        "minimum_specificity_score": 0.38,
        "maximum_ambiguity_score": 0.55,
        "required_evidence_fields": ["token_similarity", "ratio_similarity"],
    },
    "twelve_eight_gospel": {
        "minimum_confidence": 0.50,
        "strong_confidence": 0.84,
        "moderate_confidence": 0.66,
        "minimum_specificity_score": 0.38,
        "maximum_ambiguity_score": 0.55,
        "required_evidence_fields": ["token_similarity", "ratio_similarity"],
    },
    "sparse_call_response": {
        "minimum_confidence": 0.52,
        "strong_confidence": 0.82,
        "moderate_confidence": 0.62,
        "minimum_specificity_score": 0.34,
        "maximum_ambiguity_score": 0.6,
    },
    "backbeat": {
        "minimum_confidence": 0.52,
        "strong_confidence": 0.84,
        "moderate_confidence": 0.64,
        "minimum_specificity_score": 0.34,
        "maximum_ambiguity_score": 0.6,
        "required_evidence_fields": ["token_similarity", "accent_similarity"],
    },
}
