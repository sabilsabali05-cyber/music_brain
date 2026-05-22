from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.feature_dataset_common import load_json, now_iso, save_json
from scripts.trust_common import resolve_performance_context


def _safe_float(value: object, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:  # noqa: BLE001
        return fallback


def _safe_int(value: object, fallback: int = 0) -> int:
    try:
        return int(value)
    except Exception:  # noqa: BLE001
        return fallback


def _pick_asset_type(evidence: dict[str, Any]) -> tuple[str, float, list[dict[str, Any]], list[str]]:
    duration = _safe_float(evidence.get("duration_seconds"), 0.0)
    note_density = _safe_float(evidence.get("mean_note_density"), 0.0)
    polyphonic = _safe_float(evidence.get("mean_polyphonic_density"), 0.0)
    harmony_conf = _safe_float(evidence.get("mean_harmony_confidence"), 0.0)
    vocal_tag_score = _safe_float(evidence.get("vocal_tag_score"), 0.0)
    speech_tag_score = _safe_float(evidence.get("speech_tag_score"), 0.0)
    ambient_tag_score = _safe_float(evidence.get("ambient_tag_score"), 0.0)
    percussive_tag_score = _safe_float(evidence.get("percussive_tag_score"), 0.0)
    loop_like = bool(evidence.get("loop_like_structure"))

    candidates: list[tuple[str, float, str]] = [
        ("unknown", 0.2, "default fallback"),
    ]
    if duration >= 120.0:
        candidates.append(("full_song", 0.72, "long-form duration"))
    if duration >= 180.0 and _safe_int(evidence.get("segment_count"), 0) >= 3:
        candidates.append(("performance_recording", 0.8, "multi-segment long performance"))
    if vocal_tag_score >= 0.6 and speech_tag_score < 0.35:
        candidates.append(("rap_song", 0.64, "strong vocal/flow tags"))
    if speech_tag_score >= 0.55:
        candidates.append(("speech_heavy", 0.68, "speech-like tag evidence"))
    if ambient_tag_score >= 0.55 and note_density < 1.0:
        candidates.append(("ambient_texture", 0.7, "ambient tags with low note density"))
    if percussive_tag_score >= 0.55 and harmony_conf < 0.35:
        candidates.append(("drum_loop" if loop_like else "one_shot_drum", 0.66, "percussive tags with weak harmony"))
    if harmony_conf >= 0.65 and polyphonic >= 0.15:
        candidates.append(("chord_loop" if loop_like and duration < 90.0 else "full_song", 0.67, "harmonic confidence"))
    if duration <= 5.0:
        if percussive_tag_score >= 0.45:
            candidates.append(("one_shot_drum", 0.74, "very short percussive asset"))
        elif vocal_tag_score >= 0.45:
            candidates.append(("vocal_sample", 0.7, "very short vocal asset"))
        else:
            candidates.append(("one_shot_synth", 0.62, "very short non-percussive asset"))
    if duration < 60.0 and loop_like and harmony_conf < 0.5 and note_density >= 1.0:
        candidates.append(("melodic_loop", 0.6, "loop-like structure with melodic note density"))

    best = max(candidates, key=lambda item: item[1])
    alternates = sorted(candidates, key=lambda item: item[1], reverse=True)[1:4]
    limitations = []
    if _safe_int(evidence.get("ai_record_count"), 0) <= 0:
        limitations.append("No AI training records found; classification confidence reduced.")
    if _safe_int(evidence.get("window_count"), 0) <= 0:
        limitations.append("No window-level records found; asset type may be coarse.")
    return (
        best[0],
        best[1],
        [{"asset_type": item[0], "confidence": round(item[1], 4), "reason": item[2]} for item in alternates],
        limitations,
    )


def classify_audio_asset(performance_manifest_path: Path) -> Path:
    ctx = resolve_performance_context(performance_manifest_path)
    feature_dir = ctx["feature_dir"]
    routing_dir = feature_dir / "routing"
    routing_dir.mkdir(parents=True, exist_ok=True)

    segments_manifest = load_json(ctx["segments_manifest_path"])
    rhythm_payload = load_json(feature_dir / "rhythm_features.json") if (feature_dir / "rhythm_features.json").exists() else {}
    harmony_payload = load_json(feature_dir / "harmony_features.json") if (feature_dir / "harmony_features.json").exists() else {}
    tags_payload = load_json(feature_dir / "tags.json") if (feature_dir / "tags.json").exists() else {}
    reliability_payload = load_json(feature_dir / "trust" / "transcription_reliability.json") if (feature_dir / "trust" / "transcription_reliability.json").exists() else {}
    feature_summary_text = (feature_dir / "feature_summary.md").read_text(encoding="utf-8") if (feature_dir / "feature_summary.md").exists() else ""
    ai_record_count = 0
    ai_path = feature_dir / "ai_training_records.jsonl"
    if ai_path.exists():
        ai_record_count = sum(1 for line in ai_path.read_text(encoding="utf-8").splitlines() if line.strip())

    rhythm_records = rhythm_payload.get("records", [])
    harmony_records = harmony_payload.get("records", [])
    tags = tags_payload.get("tags", [])
    windows = segments_manifest.get("transcription_windows", [])
    if not isinstance(rhythm_records, list):
        rhythm_records = []
    if not isinstance(harmony_records, list):
        harmony_records = []
    if not isinstance(tags, list):
        tags = []
    if not isinstance(windows, list):
        windows = []
    reli_windows = reliability_payload.get("windows", [])
    if not isinstance(reli_windows, list):
        reli_windows = []

    rhythm_regions = [item for item in rhythm_records if isinstance(item, dict) and str(item.get("granularity")) == "rhythm_region"]
    mean_note_density = (
        sum(_safe_float((item.get("features") or {}).get("note_on_density_per_second"), 0.0) for item in rhythm_regions)
        / max(1, len(rhythm_regions))
    )
    mean_polyphonic = (
        sum(_safe_float((item.get("features") or {}).get("polyphonic_density"), 0.0) for item in rhythm_regions)
        / max(1, len(rhythm_regions))
    )
    mean_harmony_conf = (
        sum(_safe_float(item.get("confidence"), 0.0) for item in harmony_records if isinstance(item, dict))
        / max(1, len([item for item in harmony_records if isinstance(item, dict)]))
    )
    top_tags = [str(item.get("tag", "")) for item in tags if isinstance(item, dict)]
    joined_tags = " ".join(top_tags).lower()
    vocal_tag_score = 1.0 if any(key in joined_tags for key in ["rap", "vocal", "flow", "voice"]) else 0.0
    speech_tag_score = 1.0 if any(key in joined_tags for key in ["speech", "spoken"]) else 0.0
    ambient_tag_score = 1.0 if any(key in joined_tags for key in ["ambient", "texture", "drone"]) else 0.0
    percussive_tag_score = 1.0 if any(key in joined_tags for key in ["drum", "percuss", "transient", "rhythm"]) else 0.0
    duration = _safe_float(ctx["performance_manifest"].get("duration_seconds"), _safe_float(segments_manifest.get("duration_seconds"), 0.0))
    loop_like = "loop" in feature_summary_text.lower() or duration <= 64.0

    evidence = {
        "duration_seconds": duration,
        "segment_count": _safe_int(len(segments_manifest.get("musical_segments", [])) if isinstance(segments_manifest.get("musical_segments"), list) else 0),
        "window_count": len(windows),
        "successful_window_count": sum(
            1 for item in windows if isinstance(item, dict) and str(item.get("status", "pending")) == "success"
        ),
        "mean_note_density": round(mean_note_density, 6),
        "mean_polyphonic_density": round(mean_polyphonic, 6),
        "mean_harmony_confidence": round(mean_harmony_conf, 6),
        "vocal_tag_score": vocal_tag_score,
        "speech_tag_score": speech_tag_score,
        "ambient_tag_score": ambient_tag_score,
        "percussive_tag_score": percussive_tag_score,
        "loop_like_structure": loop_like,
        "transcription_reliability_windows": len(reli_windows),
        "ai_record_count": ai_record_count,
    }
    asset_type, confidence, alternate_asset_types, limitations = _pick_asset_type(evidence)
    recommended_pipeline = [
        "segment_audio",
        "transcribe_windows",
        "extract_feature_pack",
        "compute_transcription_reliability",
        "evaluate_training_quality_gates",
        "audit_training_dataset_record",
        "export_training_dataset_splits",
    ]
    should_stitch = asset_type not in {"one_shot_drum", "one_shot_synth", "vocal_sample", "speech_heavy"}
    should_segment = asset_type not in {"one_shot_drum", "one_shot_synth"}
    should_transcribe = asset_type not in {"ambient_texture", "speech_heavy"}
    recommended_max_windows = 1 if duration <= 5.0 else (2 if duration <= 60.0 else 4)
    payload = {
        "performance_id": ctx["performance_id"],
        "segment_run_id": ctx["segment_run_id"],
        "created_at": now_iso(),
        "asset_type": asset_type,
        "confidence": round(confidence, 6),
        "alternate_asset_types": alternate_asset_types,
        "evidence": evidence,
        "recommended_pipeline": recommended_pipeline,
        "recommended_max_windows": recommended_max_windows,
        "should_transcribe_with_yourmt3": should_transcribe,
        "should_segment": should_segment,
        "should_stitch": should_stitch,
        "limitations": limitations,
    }
    out_path = routing_dir / "asset_classification.json"
    save_json(out_path, payload)
    return out_path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify audio asset type from existing feature artifacts.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    args = parser.parse_args()
    output = classify_audio_asset(Path(args.performance_manifest))
    print(f"ASSET_CLASSIFICATION_PATH={output.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
