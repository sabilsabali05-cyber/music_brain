from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.feature_dataset_common import load_json, now_iso, save_json
from scripts.trust_common import load_jsonl_records, resolve_performance_context, trust_dir


WEAK_OR_REVIEW_STATUSES = {
    "weak_label",
    "heuristic_estimate",
    "interpretive_weak_label",
    "model_prediction",
}


def _safe_float(value: object, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:  # noqa: BLE001
        return fallback


def _state_for_record(record: dict[str, Any], routes: list[dict[str, Any]]) -> dict[str, Any]:
    record_id = str(record.get("record_id", ""))
    for route in routes:
        if not isinstance(route, dict):
            continue
        if str(route.get("source_record_id", "")) == record_id:
            return route
    return {}


def _label_family(label: str) -> str:
    lowered = label.lower()
    if any(token in lowered for token in ["chord", "harmony", "key", "root_motion", "vamp"]):
        return "harmony"
    if any(token in lowered for token in ["rhythm", "motif", "syncop", "groove", "density", "tempo"]):
        return "rhythm"
    if any(token in lowered for token in ["vocal", "rap", "speech", "flow"]):
        return "vocal_flow"
    return "semantic"


def _family_supported_by_route(family: str, route: dict[str, Any]) -> bool:
    allowed_families = route.get("allowed_feature_families", [])
    if not isinstance(allowed_families, list):
        return False
    if family == "harmony":
        return any(name in allowed_families for name in ["harmony", "chord_movement"])
    if family == "rhythm":
        return "rhythm" in allowed_families
    if family == "vocal_flow":
        return "vocal_flow" in allowed_families
    return "semantic" in allowed_families


def evaluate_label_upgrade_candidates(performance_manifest_path: Path) -> Path:
    ctx = resolve_performance_context(performance_manifest_path)
    feature_dir = ctx["feature_dir"]
    routing_dir = feature_dir / "routing"
    routing_decisions = load_json(routing_dir / "analysis_routing_decisions.json") if (routing_dir / "analysis_routing_decisions.json").exists() else {}
    reliability_payload = load_json(feature_dir / "trust" / "transcription_reliability.json") if (feature_dir / "trust" / "transcription_reliability.json").exists() else {}
    ai_records = load_jsonl_records(feature_dir / "ai_training_records.jsonl")
    decisions = routing_decisions.get("decisions", [])
    if not isinstance(decisions, list):
        decisions = []
    reliability_map: dict[str, dict[str, Any]] = {}
    rel_windows = reliability_payload.get("windows", [])
    if isinstance(rel_windows, list):
        for item in rel_windows:
            if isinstance(item, dict):
                win_id = str(item.get("window_id", ""))
                if win_id:
                    reliability_map[win_id] = item

    candidates: list[dict[str, Any]] = []
    counts = {
        "keep_weak": 0,
        "upgrade_candidate": 0,
        "downgrade_candidate": 0,
        "suppress_candidate": 0,
        "needs_human_review": 0,
    }
    for record in ai_records:
        if not isinstance(record, dict):
            continue
        label_status = str(record.get("label_status", ""))
        review_required = bool(record.get("review_required", False))
        if label_status not in WEAK_OR_REVIEW_STATUSES and not review_required:
            continue
        record_id = str(record.get("record_id", ""))
        route = _state_for_record(record, decisions)
        content_state = str(route.get("content_state", "unknown"))
        route_confidence = _safe_float(route.get("route_confidence"), _safe_float(route.get("confidence"), 0.0))
        confidence = _safe_float(record.get("confidence"), 0.0)
        ambiguity = _safe_float(record.get("ambiguity_score"), 0.0)
        window_id = str(record.get("window_id", ""))
        rel = reliability_map.get(window_id, {})
        rel_score = _safe_float(rel.get("transcription_reliability_score"), 0.0)
        allowed_labels = route.get("allowed_labels", []) if isinstance(route.get("allowed_labels"), list) else []
        suppressed_labels = route.get("suppressed_labels", []) if isinstance(route.get("suppressed_labels"), list) else []
        label = str(record.get("label") or record.get("tag") or record.get("best_rhythm_family_match") or "")
        family = _label_family(label)
        route_evidence = route.get("evidence", {}) if isinstance(route.get("evidence"), dict) else {}
        rhythm_score = _safe_float(route_evidence.get("rhythm_score"), 0.0)
        harmony_score = _safe_float(route_evidence.get("harmony_score"), 0.0)
        if family == "semantic" and label == "feature_ready":
            if content_state in {"harmonic_dominant", "polyphonic_full_mix"} and harmony_score >= 0.58:
                family = "harmony"
            elif content_state in {"rhythm_dominant", "percussive_only", "polyphonic_full_mix"} and rhythm_score >= 0.58:
                family = "rhythm"
        evidence_refs = record.get("evidence_refs", [])
        evidence_refs_present = isinstance(evidence_refs, list) and len(evidence_refs) > 0
        rel_tier = str(rel.get("reliability_tier", "")).lower()
        reliability_ok = rel_tier in {"high", "medium"} or rel_score >= 0.65
        route_supports_family = _family_supported_by_route(family, route)
        ambiguity_low = ambiguity <= 0.35
        confidence_ok = confidence >= 0.58

        recommended_label_status = "keep_weak"
        upgrade_reason = None
        downgrade_reason = None
        required_additional_evidence: list[str] = []
        if content_state in {"percussive_only", "ambient_low_information", "speech_like", "silence_or_noise"} and family == "harmony":
            recommended_label_status = "suppress_candidate"
            downgrade_reason = f"Harmony label conflicts with content state `{content_state}`."
            required_additional_evidence.append("strong_chord_evidence")
        elif (
            route_supports_family
            and reliability_ok
            and confidence_ok
            and ambiguity_low
            and evidence_refs_present
            and family in {"rhythm", "harmony", "semantic"}
        ):
            recommended_label_status = "upgrade_candidate"
            if family == "rhythm":
                upgrade_reason = "Rhythm-aligned route (e.g. dense_region family evidence) supports upgrade."
            elif family == "harmony":
                upgrade_reason = "Harmony-aligned route (e.g. repeated_chord_vamp evidence) supports upgrade."
            else:
                upgrade_reason = "Route, reliability, confidence, ambiguity, and evidence references support upgrade."
        elif family == "rhythm" and ambiguity >= 0.45:
            recommended_label_status = "keep_weak"
            downgrade_reason = "Rhythm-family match remains ambiguous; retain weak/review status."
            required_additional_evidence.append("disambiguated_rhythm_family")
        elif ambiguity >= 0.55:
            recommended_label_status = "needs_human_review"
            downgrade_reason = "High ambiguity score."
            required_additional_evidence.append("manual_label_review")
        elif not route_supports_family:
            recommended_label_status = "downgrade_candidate"
            downgrade_reason = "Route suitability does not support label family."
            required_additional_evidence.append("route_compatible_label_family")
        elif not evidence_refs_present:
            recommended_label_status = "downgrade_candidate"
            downgrade_reason = "Missing evidence_refs for upgrade eligibility."
            required_additional_evidence.append("evidence_refs")
        elif confidence < 0.4 or rel_score < 0.45:
            recommended_label_status = "downgrade_candidate"
            downgrade_reason = "Low confidence or transcription reliability."
            required_additional_evidence.append("higher_reliability_window")

        if suppressed_labels and family == "harmony":
            required_additional_evidence.append("route_override_justification")
        if not allowed_labels:
            required_additional_evidence.append("route_alignment_evidence")

        counts[recommended_label_status] = counts.get(recommended_label_status, 0) + 1
        candidates.append(
            {
                "candidate_id": f"{record_id}:upgrade_eval",
                "source_label_id": record_id,
                "current_label_status": label_status if label_status else ("review_required" if review_required else "unknown"),
                "recommended_label_status": recommended_label_status,
                "route_content_state": content_state,
                "route_confidence": route_confidence,
                "label_family": family,
                "upgrade_reason": upgrade_reason,
                "downgrade_reason": downgrade_reason,
                "required_additional_evidence": sorted(set(required_additional_evidence)),
                "evidence_refs": evidence_refs if isinstance(evidence_refs, list) else [],
                "versioning_note": "Scaffold recommendation only; do not overwrite original labels.",
                "do_not_overwrite_original": True,
            }
        )

    payload = {
        "performance_id": ctx["performance_id"],
        "segment_run_id": ctx["segment_run_id"],
        "created_at": now_iso(),
        "candidate_count": len(candidates),
        "summary": counts,
        "candidates": candidates,
    }
    out_path = trust_dir(feature_dir) / "label_upgrade_candidates.json"
    save_json(out_path, payload)
    return out_path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate weak/review labels for upgrade/downgrade candidates.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    args = parser.parse_args()
    output = evaluate_label_upgrade_candidates(Path(args.performance_manifest))
    print(f"LABEL_UPGRADE_CANDIDATES_PATH={output.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
