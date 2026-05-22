from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.routing.content_state_schema import make_route_decision
from scripts.feature_dataset_common import load_json, now_iso, save_json
from scripts.trust_common import load_jsonl_records, resolve_performance_context


def _safe_float(value: object, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:  # noqa: BLE001
        return fallback


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _score_bundle(evidence: dict[str, Any]) -> dict[str, float]:
    note_on = _safe_float(evidence.get("note_on_count"), 0.0)
    density = _safe_float(evidence.get("note_on_density_per_second"), 0.0)
    poly = _safe_float(evidence.get("polyphonic_density"), 0.0)
    silence = _safe_float(evidence.get("silence_ratio"), _safe_float(evidence.get("silence_ratio_proxy"), 0.0))
    chord_conf = _safe_float(evidence.get("chord_confidence"), 0.0)
    pitch_classes = _safe_float(evidence.get("active_pitch_classes_count"), 0.0)
    harmonic_activity = _safe_float(evidence.get("harmonic_activity"), 0.0)
    motif_evidence = 1.0 if evidence.get("motif_evidence") else 0.0
    rhythm_tag_score = _safe_float(evidence.get("rhythm_tag_score"), 0.0)
    transition_score = _safe_float(evidence.get("transition_score"), 0.0)
    source_confidence = _safe_float(evidence.get("source_confidence"), 0.0)
    duration = _safe_float(evidence.get("duration_seconds"), 0.0)
    missing_feature_penalty = 1.0 if bool(evidence.get("missing_feature_fields")) else 0.0
    chord_candidates_present = 1.0 if _safe_float(evidence.get("chord_candidates_present"), 0.0) > 0.0 else 0.0
    pitch_movement = _clamp01(_safe_float(evidence.get("pitch_movement"), 0.0))

    density_norm = _clamp01(density / 3.0)
    note_norm = _clamp01(note_on / 32.0)
    poly_norm = _clamp01(poly)
    pitch_norm = _clamp01(pitch_classes / 7.0)
    harmonic_activity_norm = _clamp01(harmonic_activity / 3.0)
    moderate_density = _clamp01(1.0 - abs(density - 1.4) / 1.4)
    low_confidence = _clamp01(1.0 - source_confidence)
    tiny_duration = 1.0 if 0.0 < duration <= 1.0 else 0.0

    rhythm_score = _clamp01(
        (0.34 * density_norm)
        + (0.22 * note_norm)
        + (0.18 * motif_evidence)
        + (0.16 * rhythm_tag_score)
        + (0.10 * _clamp01(1.0 - silence))
    )
    harmony_score = _clamp01(
        (0.26 * pitch_norm)
        + (0.29 * _clamp01(chord_conf))
        + (0.2 * harmonic_activity_norm)
        + (0.15 * poly_norm)
        + (0.1 * chord_candidates_present)
    )
    melody_score = _clamp01(
        (0.3 * pitch_norm)
        + (0.25 * moderate_density)
        + (0.25 * _clamp01(1.0 - poly_norm))
        + (0.2 * pitch_movement)
    )
    low_information_score = _clamp01(
        (0.33 * _clamp01(silence))
        + (0.24 * _clamp01(1.0 - note_norm))
        + (0.18 * missing_feature_penalty)
        + (0.15 * low_confidence)
        + (0.1 * tiny_duration)
    )
    polyphonic_full_mix_score = _clamp01(
        (0.34 * rhythm_score)
        + (0.34 * harmony_score)
        + (0.2 * poly_norm)
        + (0.12 * note_norm)
    )
    return {
        "rhythm_score": rhythm_score,
        "harmony_score": harmony_score,
        "melody_score": melody_score,
        "low_information_score": low_information_score,
        "polyphonic_full_mix_score": polyphonic_full_mix_score,
        "transition_score": _clamp01(transition_score),
    }


def classify_evidence_state(evidence: dict[str, Any]) -> dict[str, Any]:
    note_on = _safe_float(evidence.get("note_on_count"), 0.0)
    density = _safe_float(evidence.get("note_on_density_per_second"), 0.0)
    poly = _safe_float(evidence.get("polyphonic_density"), 0.0)
    silence = _safe_float(evidence.get("silence_ratio"), _safe_float(evidence.get("silence_ratio_proxy"), 0.0))
    chord_conf = _safe_float(evidence.get("chord_confidence"), 0.0)
    pitch_classes = _safe_float(evidence.get("active_pitch_classes_count"), 0.0)
    vocal_score = _safe_float(evidence.get("vocal_score"), 0.0)
    rap_score = _safe_float(evidence.get("rap_score"), 0.0)
    speech_score = _safe_float(evidence.get("speech_score"), 0.0)
    scores = _score_bundle(evidence)
    rhythm_score = scores["rhythm_score"]
    harmony_score = scores["harmony_score"]
    melody_score = scores["melody_score"]
    low_info = scores["low_information_score"]
    poly_mix = scores["polyphonic_full_mix_score"]
    transition_score = scores["transition_score"]

    state = "unknown"
    confidence = 0.45
    if low_info >= 0.83 and note_on <= 1 and harmony_score < 0.3 and rhythm_score < 0.42:
        state = "silence_or_noise"
        confidence = 0.86
    elif speech_score >= 0.72 and harmony_score < 0.35:
        state = "speech_like"
        confidence = 0.8
    elif rap_score >= 0.58 and rhythm_score >= 0.45:
        state = "rap_vocal_dominant"
        confidence = 0.78
    elif vocal_score >= 0.62 and rhythm_score >= 0.35:
        state = "vocal_dominant"
        confidence = 0.74
    elif poly_mix >= 0.68:
        state = "polyphonic_full_mix"
        confidence = min(0.9, 0.65 + (poly_mix - 0.68))
    elif harmony_score >= 0.62 and (harmony_score - rhythm_score) >= 0.08:
        state = "harmonic_dominant"
        confidence = min(0.88, 0.62 + (harmony_score - 0.62))
    elif rhythm_score >= 0.62 and harmony_score < 0.52:
        if pitch_classes <= 3 and chord_conf < 0.45 and poly < 0.18:
            state = "percussive_only"
            confidence = min(0.86, 0.66 + (rhythm_score - 0.62))
        else:
            state = "rhythm_dominant"
            confidence = min(0.84, 0.62 + (rhythm_score - 0.62))
    elif melody_score >= 0.58 and harmony_score >= 0.42:
        state = "melodic_lead"
        confidence = min(0.8, 0.58 + (melody_score - 0.58))
    elif low_info >= 0.5 and note_on <= 10 and silence >= 0.4 and harmony_score < 0.65:
        state = "ambient_low_information"
        confidence = min(0.82, 0.58 + (low_info - 0.5))
    elif transition_score >= 0.64:
        state = "transition_build"
        confidence = 0.7

    ranking = sorted(
        [
            ("silence_or_noise", low_info),
            ("polyphonic_full_mix", poly_mix),
            ("harmonic_dominant", harmony_score),
            ("rhythm_dominant", rhythm_score),
            ("melodic_lead", melody_score),
            ("ambient_low_information", low_info * 0.92),
            ("percussive_only", rhythm_score * (1.0 - min(1.0, harmony_score + 0.1))),
            ("speech_like", speech_score),
            ("vocal_dominant", vocal_score),
            ("rap_vocal_dominant", rap_score),
            ("transition_build", transition_score),
            ("unknown", 0.3),
        ],
        key=lambda item: item[1],
        reverse=True,
    )
    top_score = ranking[0][1] if ranking else 0.0
    second_score = ranking[1][1] if len(ranking) > 1 else 0.0
    decision_margin = _clamp01(top_score - second_score)
    alternates = [
        {"content_state": name, "score": round(score, 6)}
        for name, score in ranking
        if name != state
    ][:3]
    return {
        "content_state": state,
        "confidence": round(float(_clamp01(confidence)), 6),
        "scores": {
            "rhythm_score": round(rhythm_score, 6),
            "harmony_score": round(harmony_score, 6),
            "melody_score": round(melody_score, 6),
            "low_information_score": round(low_info, 6),
            "polyphonic_full_mix_score": round(poly_mix, 6),
        },
        "decision_margin": round(decision_margin, 6),
        "alternate_content_states": alternates,
    }


def _tag_scores_for_range(tags: list[dict[str, Any]], start_seconds: float, end_seconds: float) -> dict[str, float]:
    window_tags = []
    for item in tags:
        if not isinstance(item, dict):
            continue
        tag_start = _safe_float(item.get("start_seconds"), -1.0)
        tag_end = _safe_float(item.get("end_seconds"), -1.0)
        if tag_start < 0 or tag_end < 0:
            continue
        if tag_end < start_seconds or tag_start > end_seconds:
            continue
        window_tags.append(str(item.get("tag", "")).lower())
    joined = " ".join(window_tags)
    rhythm_tag = 1.0 if any(key in joined for key in ["rhythm", "drum", "percuss", "motif", "groove"]) else 0.0
    return {
        "vocal_score": 1.0 if any(key in joined for key in ["vocal", "voice", "singer"]) else 0.0,
        "rap_score": 1.0 if "rap" in joined or "flow" in joined else 0.0,
        "speech_score": 1.0 if "speech" in joined or "spoken" in joined else 0.0,
        "transition_score": 1.0 if "transition" in joined or "build" in joined else 0.0,
        "rhythm_tag_score": rhythm_tag,
    }


def _source_record_id(
    *,
    ai_records: list[dict[str, Any]],
    granularity: str,
    start_seconds: float,
    end_seconds: float,
) -> str | None:
    for record in ai_records:
        if not isinstance(record, dict):
            continue
        if str(record.get("granularity", "")) != granularity:
            continue
        start = _safe_float(record.get("start_seconds"), -1.0)
        end = _safe_float(record.get("end_seconds"), -1.0)
        if abs(start - start_seconds) <= 0.15 and abs(end - end_seconds) <= 0.15:
            return str(record.get("record_id"))
    return None


def classify_content_regions(performance_manifest_path: Path) -> Path:
    ctx = resolve_performance_context(performance_manifest_path)
    feature_dir = ctx["feature_dir"]
    routing_dir = feature_dir / "routing"
    routing_dir.mkdir(parents=True, exist_ok=True)

    segments_manifest = load_json(ctx["segments_manifest_path"])
    rhythm_payload = load_json(feature_dir / "rhythm_features.json") if (feature_dir / "rhythm_features.json").exists() else {}
    harmony_payload = load_json(feature_dir / "harmony_features.json") if (feature_dir / "harmony_features.json").exists() else {}
    tags_payload = load_json(feature_dir / "tags.json") if (feature_dir / "tags.json").exists() else {}
    ai_records = load_jsonl_records(feature_dir / "ai_training_records.jsonl")

    routes: list[dict[str, Any]] = []
    tags = tags_payload.get("tags", [])
    if not isinstance(tags, list):
        tags = []
    harmony_records = harmony_payload.get("records", [])
    if not isinstance(harmony_records, list):
        harmony_records = []
    harmony_by_region: dict[str, dict[str, Any]] = {}
    for item in harmony_records:
        if not isinstance(item, dict):
            continue
        region_id = str(item.get("region_id", ""))
        if region_id:
            harmony_by_region[region_id] = item

    def add_route(
        *,
        granularity: str,
        source_record_id: str | None,
        start_seconds: float,
        end_seconds: float,
        evidence: dict[str, Any],
        suffix: str,
    ) -> None:
        classification = classify_evidence_state(evidence)
        state = str(classification["content_state"])
        confidence = float(classification["confidence"])
        enriched_evidence = {
            **evidence,
            **classification["scores"],
            "decision_margin": classification["decision_margin"],
            "alternate_content_states": classification["alternate_content_states"],
        }
        decision = make_route_decision(content_state=state, confidence=confidence, evidence=enriched_evidence, limitations=[])
        routes.append(
            {
                "route_id": f"{ctx['performance_id']}:{granularity}:{suffix}",
                "granularity": granularity,
                "source_record_id": source_record_id,
                "start_seconds": round(start_seconds, 6),
                "end_seconds": round(end_seconds, 6),
                "decision_margin": classification["decision_margin"],
                "alternate_content_states": classification["alternate_content_states"],
                **decision,
            }
        )

    segments = segments_manifest.get("musical_segments", [])
    if isinstance(segments, list):
        for idx, segment in enumerate(segments):
            if not isinstance(segment, dict):
                continue
            start_seconds = _safe_float(segment.get("global_start_seconds"), _safe_float(segment.get("start_seconds"), 0.0))
            end_seconds = _safe_float(segment.get("global_end_seconds"), _safe_float(segment.get("end_seconds"), start_seconds))
            tag_scores = _tag_scores_for_range([item for item in tags if isinstance(item, dict)], start_seconds, end_seconds)
            evidence = {
                "note_on_count": _safe_float(segment.get("note_on_count"), 0.0),
                "note_on_density_per_second": _safe_float(segment.get("note_on_density_per_second"), 0.0),
                "polyphonic_density": _safe_float(segment.get("polyphonic_density"), 0.0),
                "silence_ratio": _safe_float(segment.get("silence_ratio"), 0.0),
                "chord_confidence": _safe_float(segment.get("boundary_confidence"), 0.0),
                "active_pitch_classes_count": _safe_float(segment.get("active_pitch_classes_count"), 0.0),
                "duration_seconds": max(0.0, end_seconds - start_seconds),
                "source_confidence": _safe_float(segment.get("boundary_confidence"), 0.0),
                "missing_feature_fields": False,
                "pitch_movement": _safe_float(segment.get("pitch_movement"), 0.0),
                "chord_candidates_present": 1.0 if _safe_float(segment.get("active_pitch_classes_count"), 0.0) >= 3 else 0.0,
                **tag_scores,
            }
            add_route(
                granularity="segment",
                source_record_id=_source_record_id(
                    ai_records=ai_records,
                    granularity="segment",
                    start_seconds=start_seconds,
                    end_seconds=end_seconds,
                ),
                start_seconds=start_seconds,
                end_seconds=end_seconds,
                evidence=evidence,
                suffix=f"segment_{idx:04d}",
            )

    windows = segments_manifest.get("transcription_windows", [])
    if isinstance(windows, list):
        for idx, window in enumerate(windows):
            if not isinstance(window, dict):
                continue
            start_seconds = _safe_float(window.get("core_start_seconds"), _safe_float(window.get("global_start_seconds"), 0.0))
            end_seconds = _safe_float(window.get("core_end_seconds"), _safe_float(window.get("global_end_seconds"), start_seconds))
            tag_scores = _tag_scores_for_range([item for item in tags if isinstance(item, dict)], start_seconds, end_seconds)
            evidence = {
                "note_on_count": _safe_float(window.get("note_on_count"), 0.0),
                "note_on_density_per_second": _safe_float(window.get("note_on_density_per_second"), 0.0),
                "polyphonic_density": _safe_float(window.get("polyphonic_density"), 0.0),
                "silence_ratio_proxy": _safe_float(window.get("silence_ratio_proxy"), 0.0),
                "chord_confidence": _safe_float(window.get("chord_confidence"), 0.0),
                "active_pitch_classes_count": _safe_float(window.get("active_pitch_classes_count"), 0.0),
                "duration_seconds": max(0.0, end_seconds - start_seconds),
                "source_confidence": _safe_float(window.get("confidence"), 0.0),
                "missing_feature_fields": False,
                "pitch_movement": _safe_float(window.get("pitch_movement"), 0.0),
                "chord_candidates_present": 1.0 if _safe_float(window.get("active_pitch_classes_count"), 0.0) >= 3 else 0.0,
                **tag_scores,
            }
            add_route(
                granularity="window",
                source_record_id=_source_record_id(
                    ai_records=ai_records,
                    granularity="window",
                    start_seconds=start_seconds,
                    end_seconds=end_seconds,
                ),
                start_seconds=start_seconds,
                end_seconds=end_seconds,
                evidence=evidence,
                suffix=f"window_{idx:04d}",
            )

    rhythm_records = rhythm_payload.get("records", [])
    if isinstance(rhythm_records, list):
        regions = [
            item
            for item in rhythm_records
            if isinstance(item, dict) and str(item.get("granularity", "")) == "rhythm_region"
        ]
        for idx, region in enumerate(regions):
            start_seconds = _safe_float(region.get("start_seconds"), 0.0)
            end_seconds = _safe_float(region.get("end_seconds"), start_seconds)
            features = region.get("features", {}) if isinstance(region.get("features"), dict) else {}
            harmony_match = harmony_by_region.get(str(region.get("region_id", "")), {})
            harmony_features = harmony_match.get("features", {}) if isinstance(harmony_match.get("features"), dict) else {}
            tag_scores = _tag_scores_for_range([item for item in tags if isinstance(item, dict)], start_seconds, end_seconds)
            pitch_hist = harmony_features.get("pitch_class_histogram", [])
            evidence = {
                "note_on_count": _safe_float(features.get("note_on_count"), 0.0),
                "note_on_density_per_second": _safe_float(features.get("note_on_density_per_second"), 0.0),
                "polyphonic_density": _safe_float(features.get("polyphonic_density"), 0.0),
                "silence_ratio": _safe_float(features.get("silence_ratio"), 0.0),
                "chord_confidence": _safe_float(harmony_match.get("confidence"), 0.0),
                "active_pitch_classes_count": len([v for v in pitch_hist if _safe_float(v, 0.0) > 0.0]) if isinstance(pitch_hist, list) else 0,
                "harmonic_activity": _safe_float(harmony_features.get("chord_change_count"), 0.0),
                "motif_evidence": bool(region.get("motif_id") or region.get("motif_group_id")),
                "duration_seconds": max(0.0, end_seconds - start_seconds),
                "source_confidence": _safe_float(region.get("confidence"), 0.0),
                "missing_feature_fields": not bool(features),
                "pitch_movement": _safe_float(features.get("pitch_movement"), 0.0),
                "chord_candidates_present": 1.0 if _safe_float(harmony_features.get("chord_change_count"), 0.0) > 0 else 0.0,
                **tag_scores,
            }
            add_route(
                granularity="rhythm_region",
                source_record_id=_source_record_id(
                    ai_records=ai_records,
                    granularity="rhythm_region",
                    start_seconds=start_seconds,
                    end_seconds=end_seconds,
                ),
                start_seconds=start_seconds,
                end_seconds=end_seconds,
                evidence=evidence,
                suffix=f"rhythm_region_{idx:04d}",
            )

    if isinstance(harmony_records, list):
        chord_regions = [
            item
            for item in harmony_records
            if isinstance(item, dict) and str(item.get("granularity", "")) == "chord_region"
        ]
        for idx, region in enumerate(chord_regions):
            start_seconds = _safe_float(region.get("start_seconds"), 0.0)
            end_seconds = _safe_float(region.get("end_seconds"), start_seconds)
            features = region.get("features", {}) if isinstance(region.get("features"), dict) else {}
            pitch_hist = features.get("pitch_class_histogram", [])
            note_on_count = _safe_float(features.get("note_on_count"), 0.0)
            duration = max(0.001, end_seconds - start_seconds)
            tag_scores = _tag_scores_for_range([item for item in tags if isinstance(item, dict)], start_seconds, end_seconds)
            evidence = {
                "note_on_count": note_on_count,
                "note_on_density_per_second": note_on_count / duration,
                "polyphonic_density": _safe_float(features.get("repeated_root"), 0.0),
                "silence_ratio": 0.0,
                "chord_confidence": _safe_float(region.get("confidence"), 0.0),
                "active_pitch_classes_count": len([v for v in pitch_hist if _safe_float(v, 0.0) > 0.0]) if isinstance(pitch_hist, list) else 0,
                "harmonic_activity": _safe_float(features.get("chord_change_count"), 0.0),
                "duration_seconds": max(0.0, end_seconds - start_seconds),
                "source_confidence": _safe_float(region.get("confidence"), 0.0),
                "missing_feature_fields": not bool(features),
                "pitch_movement": _safe_float(features.get("stepwise_root_motion_score"), 0.0),
                "chord_candidates_present": 1.0 if _safe_float(features.get("chord_change_count"), 0.0) > 0 else 0.0,
                **tag_scores,
            }
            add_route(
                granularity="chord_region",
                source_record_id=_source_record_id(
                    ai_records=ai_records,
                    granularity="chord_region",
                    start_seconds=start_seconds,
                    end_seconds=end_seconds,
                ),
                start_seconds=start_seconds,
                end_seconds=end_seconds,
                evidence=evidence,
                suffix=f"chord_region_{idx:04d}",
            )

    counts: dict[str, int] = {}
    for item in routes:
        state = str(item.get("content_state", "unknown"))
        counts[state] = counts.get(state, 0) + 1
    payload = {
        "performance_id": ctx["performance_id"],
        "segment_run_id": ctx["segment_run_id"],
        "created_at": now_iso(),
        "route_count": len(routes),
        "content_state_counts": counts,
        "routes": routes,
    }
    out_path = routing_dir / "content_region_routes.json"
    save_json(out_path, payload)
    return out_path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify segment/window/region content states from feature artifacts.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    args = parser.parse_args()
    output = classify_content_regions(Path(args.performance_manifest))
    print(f"CONTENT_REGION_ROUTES_PATH={output.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
