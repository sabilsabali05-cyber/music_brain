from __future__ import annotations

from typing import Any

POLICY_VERSION = "field_trust_policy_v1"

ACCEPTED_OBSERVATION_FIELDS = {
    "record_id",
    "performance_id",
    "segment_run_id",
    "granularity",
    "start_seconds",
    "end_seconds",
    "duration_seconds",
    "audio_ref",
    "midi_ref",
    "merged_midi_ref",
    "window_id",
    "segment_id",
    "note_on_count",
    "note_on_density_per_second",
    "velocity_mean",
    "velocity_std",
    "pitch_class_histogram",
    "pitch_range",
    "pitch_class_summary",
    "interval_class_summary",
    "register_summary",
    "voicing_span",
    "note_density_polyphony",
    "voice_count_estimate",
    "polyphonic_density",
    "silence_ratio_proxy",
    "transcription_reliability_score",
    "recommended_training_weight",
    "provenance",
    "feature_refs",
}

WEAK_LABEL_FIELDS = {
    "chord_candidates",
    "chord_label_candidate",
    "key_estimate",
    "rhythm_family_matches",
    "best_rhythm_family_match",
    "motif_group_refs",
    "rhythm_concepts",
    "philosophy_sources",
    "label",
    "tag",
    "sonority_type_candidate",
    "contour_summary",
    "voice_leading_summary",
    "counterpoint_summary",
    "tuning_summary",
    "pitch_harmony_refs",
    "cadence_modulation_candidates",
    "macro_key_hypotheses",
}

REVIEW_REQUIRED_FIELDS = {
    "ambiguous_family_candidates",
    "ambiguity_score",
    "mismatch_reasons",
    "syncopation_proxy_score",
    "repetition_proxy_score",
    "external_conflict_warnings",
}

WEAK_LABEL_STATUSES = {"weak_label", "heuristic_estimate", "interpretive_weak_label", "model_prediction"}
QUARANTINE_CONDITIONS = {
    "missing record_id",
    "invalid time range",
    "missing performance_id",
    "malformed JSON",
    "failed/missing MIDI for MIDI-dependent record",
    "critical schema/provenance failure",
}


def _safe_float(value: object, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:  # noqa: BLE001
        return fallback


def _time_range_valid(record: dict[str, Any]) -> bool:
    if "start_seconds" not in record or "end_seconds" not in record:
        return False
    try:
        return float(record.get("end_seconds")) >= float(record.get("start_seconds"))
    except Exception:  # noqa: BLE001
        return False


def should_quarantine_record(record: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if not str(record.get("record_id", "")).strip():
        reasons.append("missing record_id")
    if not str(record.get("performance_id", "")).strip():
        reasons.append("missing performance_id")
    if not _time_range_valid(record):
        reasons.append("invalid time range")
    source_paths = record.get("source_artifact_paths", {})
    if not isinstance(source_paths, dict):
        reasons.append("missing source_artifact_paths")
    if "feature_version" not in record:
        reasons.append("missing feature_version")
    return (len(reasons) > 0, reasons)


def _record_reliability(record: dict[str, Any], reliability_lookup: dict[str, dict[str, Any]]) -> tuple[str, float, float]:
    window_id = str(record.get("window_id", "") or "")
    rel = reliability_lookup.get(window_id, {})
    if not rel and record.get("granularity") in {"performance", "segment"}:
        # Performance/segment records can inherit high trust when windows are healthy.
        return ("high", 0.95, 1.0)
    tier = str(rel.get("reliability_tier", "low"))
    score = _safe_float(rel.get("transcription_reliability_score"), 0.0)
    weight = _safe_float(rel.get("recommended_training_weight"), 0.0)
    return (tier, score, weight)


def classify_record_for_export(
    record: dict[str, Any],
    reliability_lookup: dict[str, dict[str, Any]],
    quality_gates: dict[str, Any],
) -> dict[str, Any]:
    quarantine, quarantine_reasons = should_quarantine_record(record)
    if quarantine:
        return {"split": "quarantined_records", "reasons": quarantine_reasons}

    gate_status = str(quality_gates.get("overall_quality_status", "review_required"))
    tier, score, weight = _record_reliability(record, reliability_lookup)
    label_status = str(record.get("label_status", "weak_label"))
    confidence = _safe_float(record.get("confidence"), 0.0)
    reasons: list[str] = []
    if gate_status == "quarantined":
        reasons.append("quality gates quarantined this performance")
        return {"split": "review_required_records", "reasons": reasons, "tier": tier, "score": score, "weight": weight}

    if label_status == "human_verified_label":
        return {"split": "accepted_records", "reasons": ["human verified label"], "tier": tier, "score": score, "weight": max(weight, 0.9)}

    if label_status in WEAK_LABEL_STATUSES:
        if confidence < 0.35 or tier in {"low", "missing", "failed"}:
            reasons.append("weak/heuristic label with insufficient confidence or reliability")
            return {"split": "review_required_records", "reasons": reasons, "tier": tier, "score": score, "weight": weight}
        return {"split": "weak_label_records", "reasons": ["weak label separated from accepted observations"], "tier": tier, "score": score, "weight": min(weight, 0.7)}

    if label_status in {"raw_observation", "derived_observation"} and tier in {"high", "medium"} and confidence >= 0.4:
        return {"split": "accepted_records", "reasons": ["high/medium reliability observation record"], "tier": tier, "score": score, "weight": max(weight, 0.7)}

    if tier in {"high", "medium"} and confidence >= 0.4:
        return {"split": "audio_midi_only_records", "reasons": ["reliable timing/transcription context without safe labels"], "tier": tier, "score": score, "weight": max(weight, 0.6)}

    reasons.append("ambiguous or low-confidence record")
    return {"split": "review_required_records", "reasons": reasons, "tier": tier, "score": score, "weight": weight}


def make_accepted_observation_record(record: dict[str, Any], reliability_lookup: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    tier, score, weight = _record_reliability(record, reliability_lookup)
    source_paths = record.get("source_artifact_paths", {})
    if not isinstance(source_paths, dict):
        source_paths = {}
    features = record.get("input_features", {})
    rhythm_excerpt = features.get("rhythm_excerpt", {}) if isinstance(features, dict) and isinstance(features.get("rhythm_excerpt"), dict) else {}
    harmony_excerpt = features.get("harmony_excerpt", {}) if isinstance(features, dict) and isinstance(features.get("harmony_excerpt"), dict) else {}
    pitch_harmony_excerpt = (
        features.get("pitch_harmony_excerpt", {})
        if isinstance(features, dict) and isinstance(features.get("pitch_harmony_excerpt"), dict)
        else {}
    )

    accepted = {
        "record_id": record.get("record_id"),
        "performance_id": record.get("performance_id"),
        "segment_run_id": record.get("segment_run_id"),
        "granularity": record.get("granularity"),
        "start_seconds": record.get("start_seconds"),
        "end_seconds": record.get("end_seconds"),
        "duration_seconds": record.get("duration_seconds"),
        "window_id": record.get("window_id"),
        "segment_id": record.get("segment_id"),
        "audio_ref": source_paths.get("performance_manifest_path"),
        "midi_ref": source_paths.get("merged_midi_path") or source_paths.get("segments_manifest_path"),
        "merged_midi_ref": source_paths.get("merged_midi_path"),
        "note_on_count": rhythm_excerpt.get("note_on_count"),
        "note_on_density_per_second": rhythm_excerpt.get("note_density_per_second"),
        "velocity_mean": rhythm_excerpt.get("velocity_mean"),
        "velocity_std": rhythm_excerpt.get("velocity_std"),
        "pitch_class_histogram": harmony_excerpt.get("pitch_class_histogram"),
        "pitch_range": pitch_harmony_excerpt.get("pitch_range") or record.get("pitch_range"),
        "pitch_class_summary": pitch_harmony_excerpt.get("pitch_class_summary") or record.get("pitch_class_summary"),
        "interval_class_summary": pitch_harmony_excerpt.get("interval_class_summary") or record.get("interval_class_summary"),
        "register_summary": pitch_harmony_excerpt.get("register_summary") or record.get("register_summary"),
        "voicing_span": (pitch_harmony_excerpt.get("voice_leading_summary", {}) or {}).get("average_abs_melodic_motion")
        if isinstance(pitch_harmony_excerpt.get("voice_leading_summary"), dict)
        else None,
        "note_density_polyphony": {
            "note_on_density_per_second": rhythm_excerpt.get("note_density_per_second"),
            "polyphonic_density": rhythm_excerpt.get("polyphonic_density"),
        },
        "voice_count_estimate": (record.get("counterpoint_summary", {}) or {}).get("voice_count_estimate")
        if isinstance(record.get("counterpoint_summary"), dict)
        else None,
        "polyphonic_density": rhythm_excerpt.get("polyphonic_density"),
        "silence_ratio_proxy": rhythm_excerpt.get("silence_ratio_proxy"),
        "transcription_reliability_score": score,
        "recommended_training_weight": weight,
        "provenance": {
            "feature_version": record.get("feature_version"),
            "extractor_name": record.get("extractor_name"),
            "created_at": record.get("created_at"),
            "source_artifact_paths": source_paths,
        },
        "feature_refs": record.get("feature_refs", {}),
        "pitch_harmony_refs": record.get("pitch_harmony_refs", {}),
        "label_status": "raw_observation" if str(record.get("label_status", "")) == "raw_observation" else "derived_observation",
        "verification_status": record.get("verification_status", "unverified"),
        "confidence": record.get("confidence"),
        "confidence_reason": "field-trust export of observation-only subset.",
        "limitations": record.get("limitations", []),
    }
    excluded_fields = sorted(set(record.keys()) - set(accepted.keys()))
    return accepted, excluded_fields


def make_weak_label_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_id": record.get("record_id"),
        "performance_id": record.get("performance_id"),
        "segment_run_id": record.get("segment_run_id"),
        "granularity": record.get("granularity"),
        "window_id": record.get("window_id"),
        "start_seconds": record.get("start_seconds"),
        "end_seconds": record.get("end_seconds"),
        "duration_seconds": record.get("duration_seconds"),
        "label_status": record.get("label_status", "weak_label"),
        "label": record.get("label") or record.get("tag"),
        "evidence_refs": record.get("evidence_refs", []),
        "confidence": record.get("confidence"),
        "confidence_reason": record.get("confidence_reason"),
        "limitations": record.get("limitations", []),
        "source_record_ref": record.get("record_id"),
        "weak_fields": {k: record.get(k) for k in WEAK_LABEL_FIELDS if k in record},
    }


def make_review_required_record(record: dict[str, Any], reasons: list[str]) -> dict[str, Any]:
    return {
        **record,
        "review_reasons": reasons,
    }
