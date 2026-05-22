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


def _routing_for_state(content_state: str) -> tuple[list[str], list[str], list[str], list[str], str]:
    if content_state == "percussive_only":
        return (
            ["rhythm_family", "tempo_grid", "swing_groove", "transient_density"],
            ["hard_chord_label", "key_signature_label", "root_motion_label"],
            ["rhythm", "transient", "tempo_grid", "swing_groove", "semantic", "training_export"],
            ["harmony", "chord_movement", "melody"],
            "observation_priority",
        )
    if content_state == "rhythm_dominant":
        return (
            ["rhythm_family", "motif_presence", "density_band"],
            ["hard_chord_label"],
            ["rhythm", "tempo_grid", "swing_groove", "transient", "semantic", "training_export"],
            ["chord_movement"],
            "weak_harmony_labels_without_support",
        )
    if content_state == "harmonic_dominant":
        return (
            ["chord_label_candidate", "key_estimate", "root_motion_pattern", "rhythm_density"],
            [],
            ["harmony", "chord_movement", "melody", "rhythm", "semantic", "training_export"],
            ["transient"],
            "balanced_music_labels_with_evidence",
        )
    if content_state in {"vocal_dominant", "rap_vocal_dominant"}:
        return (
            ["vocal_flow", "phrase_density", "rhythm_pattern"],
            ["hard_chord_label"],
            ["vocal_flow", "rhythm", "semantic", "timbre", "training_export"],
            ["chord_movement", "melody"],
            "vocal_label_priority",
        )
    if content_state == "ambient_low_information":
        return (
            ["texture_descriptor", "timbre_cluster"],
            ["hard_chord_label", "hard_tempo_label", "strict_groove_label"],
            ["texture", "timbre", "semantic", "training_export"],
            ["harmony", "chord_movement", "tempo_grid", "swing_groove"],
            "low_information_conservative",
        )
    if content_state == "speech_like":
        return (
            ["speech_rhythm_proxy", "phrase_timing"],
            ["hard_chord_label", "key_signature_label", "root_motion_label"],
            ["vocal_flow", "semantic", "timbre", "training_export"],
            ["harmony", "melody", "chord_movement"],
            "review_required_music_labels",
        )
    if content_state == "polyphonic_full_mix":
        return (
            ["chord_label_candidate", "rhythm_family", "motif_presence", "key_estimate"],
            [],
            ["rhythm", "harmony", "chord_movement", "melody", "semantic", "training_export"],
            [],
            "full_stack_with_confidence_thresholds",
        )
    if content_state == "silence_or_noise":
        return (
            ["silence_ratio_proxy", "noise_floor_proxy"],
            ["hard_chord_label", "hard_rhythm_label", "hard_key_label"],
            ["texture", "semantic", "training_export"],
            ["harmony", "chord_movement", "melody", "tempo_grid", "swing_groove"],
            "suppress_music_theory_on_silence",
        )
    return (
        ["generic_timing_observation"],
        ["hard_chord_label"],
        ["semantic", "training_export"],
        ["chord_movement"],
        "default_conservative",
    )


def apply_analysis_routing(performance_manifest_path: Path) -> Path:
    ctx = resolve_performance_context(performance_manifest_path)
    feature_dir = ctx["feature_dir"]
    routing_dir = feature_dir / "routing"
    asset_path = routing_dir / "asset_classification.json"
    routes_path = routing_dir / "content_region_routes.json"
    if not asset_path.exists():
        raise FileNotFoundError(f"Missing asset classification: {asset_path}")
    if not routes_path.exists():
        raise FileNotFoundError(f"Missing content routes: {routes_path}")

    asset = load_json(asset_path)
    routes_payload = load_json(routes_path)
    routes = routes_payload.get("routes", [])
    if not isinstance(routes, list):
        routes = []

    routing_rows: list[dict[str, Any]] = []
    suppressed_label_total = 0
    for item in routes:
        if not isinstance(item, dict):
            continue
        content_state = str(item.get("content_state", "unknown"))
        allowed_labels, suppressed_labels, allowed_families, suppressed_families, policy = _routing_for_state(content_state)
        suppressed_label_total += len(suppressed_labels)
        routing_rows.append(
            {
                "route_id": item.get("route_id"),
                "source_record_id": item.get("source_record_id"),
                "granularity": item.get("granularity"),
                "start_seconds": item.get("start_seconds"),
                "end_seconds": item.get("end_seconds"),
                "content_state": content_state,
                "route_confidence": item.get("confidence"),
                "decision_margin": item.get("decision_margin"),
                "alternate_content_states": item.get("alternate_content_states", []),
                "evidence": item.get("evidence", {}),
                "allowed_labels": allowed_labels,
                "suppressed_labels": suppressed_labels,
                "allowed_feature_families": allowed_families,
                "suppressed_feature_families": suppressed_families,
                "training_label_policy": policy,
                "label_gating_rules": item.get("label_gating_rules", []),
                "limitations": item.get("limitations", []),
            }
        )

    payload = {
        "performance_id": ctx["performance_id"],
        "segment_run_id": ctx["segment_run_id"],
        "created_at": now_iso(),
        "asset_type": asset.get("asset_type", "unknown"),
        "asset_confidence": asset.get("confidence", 0.0),
        "decisions": routing_rows,
        "summary": {
            "decision_count": len(routing_rows),
            "suppressed_label_count": suppressed_label_total,
            "states_seen": sorted({str(item.get("content_state", "unknown")) for item in routing_rows}),
        },
    }
    out_path = routing_dir / "analysis_routing_decisions.json"
    save_json(out_path, payload)
    return out_path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply content-state routes into analysis/label gating decisions.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    args = parser.parse_args()
    output = apply_analysis_routing(Path(args.performance_manifest))
    print(f"ANALYSIS_ROUTING_DECISIONS_PATH={output.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
