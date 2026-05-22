from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.external_analyzer_common import external_output_dir, resolve_performance_context
from scripts.feature_dataset_common import load_json, save_json


def _safe_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = load_json(path)
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def build_model_consensus(performance_manifest_path: Path) -> dict[str, Any]:
    ctx = resolve_performance_context(performance_manifest_path)
    feature_dir = ctx["feature_dir"]
    witness_dir = external_output_dir(feature_dir)

    comparison = _safe_json(witness_dir / "model_witness_comparison.json")
    rhythm = _safe_json(feature_dir / "rhythm_features.json")
    meter_time = _safe_json(feature_dir / "rhythm_time" / "meter_time_features.json")
    pitch_harmony = _safe_json(feature_dir / "pitch_harmony" / "pitch_harmony_features.json")
    tags = _safe_json(feature_dir / "tags.json")
    beat = _safe_json(witness_dir / "beat_tracker_features.json")
    essentia = _safe_json(witness_dir / "essentia_features.json")
    music21 = _safe_json(witness_dir / "music21_features.json")
    musicnn = _safe_json(witness_dir / "musicnn_features.json")

    agreements: list[str] = []
    disagreements: list[str] = []
    confidence_boosts: list[str] = []
    confidence_penalties: list[str] = []
    unresolved_conflicts: list[str] = []
    recommended_review_items: list[str] = []

    tempo_delta = comparison.get("tempo_alignment", {}).get("delta_bpm") if isinstance(comparison.get("tempo_alignment"), dict) else None
    if tempo_delta is not None:
        try:
            delta = float(tempo_delta)
            if delta <= 8.0:
                agreements.append("Internal tempo and external beat tempo are within tolerance.")
                confidence_boosts.append("tempo_alignment")
            else:
                disagreements.append(f"Tempo disagreement ({delta:.2f} BPM delta).")
                confidence_penalties.append("tempo_conflict")
                recommended_review_items.append("Review tempo consensus for meter-sensitive labels.")
        except Exception:  # noqa: BLE001
            pass

    tonal_agreement = comparison.get("tonal_alignment", {}).get("agreement") if isinstance(comparison.get("tonal_alignment"), dict) else False
    if tonal_agreement:
        agreements.append("Internal and witness tonal center candidates align.")
        confidence_boosts.append("tonal_alignment")
    else:
        internal_key = comparison.get("tonal_alignment", {}).get("internal_key_candidate") if isinstance(comparison.get("tonal_alignment"), dict) else None
        external_key = comparison.get("tonal_alignment", {}).get("external_key_candidate") if isinstance(comparison.get("tonal_alignment"), dict) else None
        if internal_key or external_key:
            disagreements.append(f"Tonal-center disagreement: internal={internal_key} external={external_key}.")
            confidence_penalties.append("tonal_conflict")
            unresolved_conflicts.append("tonal_center_conflict")

    tag_overlap = comparison.get("tag_alignment", {}).get("overlap", []) if isinstance(comparison.get("tag_alignment"), dict) else []
    if isinstance(tag_overlap, list) and tag_overlap:
        agreements.append("Internal tags overlap with semantic witness tags.")
        confidence_boosts.append("semantic_tag_overlap")
    else:
        confidence_penalties.append("semantic_tag_mismatch")

    meter_hyp = meter_time.get("beat_meter_hypotheses", []) if isinstance(meter_time.get("beat_meter_hypotheses"), list) else []
    witness_meter = beat.get("features", {}).get("meter_hypotheses", []) if isinstance(beat.get("features"), dict) else []
    if meter_hyp and witness_meter:
        agreements.append("Meter hypothesis lists are available from both internal and witness pipelines.")
    elif meter_hyp and not witness_meter:
        unresolved_conflicts.append("missing_external_meter_hypotheses")

    key_hyp = pitch_harmony.get("macro_record", {}).get("key_hypotheses", []) if isinstance(pitch_harmony.get("macro_record"), dict) else []
    music21_keys = music21.get("features", {}).get("key_candidates", []) if isinstance(music21.get("features"), dict) else []
    if not music21_keys and isinstance(music21.get("key_candidates"), list):
        music21_keys = music21.get("key_candidates", [])
    if key_hyp and music21_keys:
        agreements.append("Symbolic key witness is present for key hypothesis comparison.")

    internal_tags = tags.get("top_unique_tags", []) if isinstance(tags.get("top_unique_tags"), list) else []
    witness_tags = musicnn.get("top_tags", []) if isinstance(musicnn.get("top_tags"), list) else []
    if internal_tags and witness_tags:
        agreements.append("Internal tags and musicnn witness both available for semantic corroboration.")

    rhythm_families = rhythm.get("rhythm_pattern_index", {}).get("top_rhythm_family_matches", []) if isinstance(rhythm.get("rhythm_pattern_index"), dict) else []
    beat_status = beat.get("status", "missing")
    if rhythm_families and beat_status == "success":
        confidence_boosts.append("rhythm_lexicon_with_beat_witness")
    elif rhythm_families and beat_status != "success":
        recommended_review_items.append("Beat witness unavailable; review rhythm family confidence manually.")

    provider_limitations = {
        "essentia": essentia.get("limitations", []),
        "musicnn": musicnn.get("limitations", []),
        "beat_tracker": beat.get("limitations", []),
        "music21": music21.get("limitations", []),
    }
    consensus_status = "monitor"
    if disagreements:
        consensus_status = "conflicted"
    elif agreements:
        consensus_status = "supportive"

    payload = {
        "performance_id": ctx["performance_id"],
        "segment_run_id": ctx["segment_run_id"],
        "agreements": agreements,
        "disagreements": disagreements,
        "confidence_boosts": sorted(set(confidence_boosts)),
        "confidence_penalties": sorted(set(confidence_penalties)),
        "unresolved_conflicts": sorted(set(unresolved_conflicts)),
        "provider_limitations": provider_limitations,
        "recommended_review_items": sorted(set(recommended_review_items)),
        "consensus_status": consensus_status,
        "consensus_is_not_ground_truth": True,
    }
    out_json = witness_dir / "model_consensus.json"
    save_json(out_json, payload)
    out_md = witness_dir / "model_consensus.md"
    out_md.write_text(
        "\n".join(
            [
                f"# Model Consensus - {ctx['performance_id']}",
                "",
                f"- consensus_status: `{consensus_status}`",
                f"- agreements: `{len(agreements)}`",
                f"- disagreements: `{len(disagreements)}`",
                f"- confidence_boosts: `{json.dumps(payload['confidence_boosts'], ensure_ascii=True)}`",
                f"- confidence_penalties: `{json.dumps(payload['confidence_penalties'], ensure_ascii=True)}`",
                f"- unresolved_conflicts: `{json.dumps(payload['unresolved_conflicts'], ensure_ascii=True)}`",
                f"- recommended_review_items: `{json.dumps(payload['recommended_review_items'], ensure_ascii=True)}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Build model consensus from internal + external witness outputs.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    args = parser.parse_args()
    payload = build_model_consensus(Path(args.performance_manifest))
    print("MODEL_CONSENSUS_JSON=" + json.dumps(payload, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
