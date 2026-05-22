from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.feature_dataset_common import load_json, now_iso, save_json
from scripts.trust_common import load_jsonl_records, resolve_performance_context, trust_dir


def _safe_float(value: object, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:  # noqa: BLE001
        return fallback


def _load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = load_json(path)
    return payload if isinstance(payload, dict) else {}


def _top_examples(routes: list[dict[str, Any]], state: str, limit: int = 10) -> list[dict[str, Any]]:
    filtered = [
        route
        for route in routes
        if isinstance(route, dict) and str(route.get("content_state", "unknown")) == state
    ]
    filtered.sort(
        key=lambda item: (
            _safe_float(item.get("evidence", {}).get("harmony_score"), 0.0),
            _safe_float(item.get("evidence", {}).get("note_on_density_per_second"), 0.0),
            _safe_float(item.get("confidence"), 0.0),
        ),
        reverse=True,
    )
    rows: list[dict[str, Any]] = []
    for item in filtered[:limit]:
        evidence = item.get("evidence", {}) if isinstance(item.get("evidence"), dict) else {}
        rows.append(
            {
                "route_id": item.get("route_id"),
                "granularity": item.get("granularity"),
                "start_seconds": item.get("start_seconds"),
                "end_seconds": item.get("end_seconds"),
                "confidence": item.get("confidence"),
                "note_on_density_per_second": evidence.get("note_on_density_per_second"),
                "active_pitch_classes_count": evidence.get("active_pitch_classes_count"),
                "chord_confidence": evidence.get("chord_confidence"),
                "polyphonic_density": evidence.get("polyphonic_density"),
                "decision_margin": evidence.get("decision_margin", item.get("decision_margin")),
            }
        )
    return rows


def diagnose_content_routing(performance_manifest_path: Path) -> tuple[Path, Path]:
    ctx = resolve_performance_context(performance_manifest_path)
    feature_dir = ctx["feature_dir"]
    routing_dir = feature_dir / "routing"
    routing_dir.mkdir(parents=True, exist_ok=True)

    routes_payload = _load_json_if_exists(routing_dir / "content_region_routes.json")
    decisions_payload = _load_json_if_exists(routing_dir / "analysis_routing_decisions.json")
    rhythm_payload = _load_json_if_exists(feature_dir / "rhythm_features.json")
    harmony_payload = _load_json_if_exists(feature_dir / "harmony_features.json")
    tags_payload = _load_json_if_exists(feature_dir / "tags.json")
    reliability_payload = _load_json_if_exists(feature_dir / "trust" / "transcription_reliability.json")
    ai_records = load_jsonl_records(feature_dir / "ai_training_records.jsonl")
    upgrade_payload = _load_json_if_exists(trust_dir(feature_dir) / "label_upgrade_candidates.json")

    routes = routes_payload.get("routes", [])
    if not isinstance(routes, list):
        routes = []
    decisions = decisions_payload.get("decisions", [])
    if not isinstance(decisions, list):
        decisions = []
    rhythm_records = rhythm_payload.get("records", [])
    harmony_records = harmony_payload.get("records", [])
    tags = tags_payload.get("tags", [])

    counts_by_granularity: dict[str, dict[str, int]] = defaultdict(dict)
    metric_sums: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    metric_counts: dict[str, int] = defaultdict(int)
    harmonic_evidence_not_harmonic: list[dict[str, Any]] = []
    likely_false_suppressions: list[dict[str, Any]] = []
    labels_suppressed_by_state: dict[str, dict[str, int]] = defaultdict(dict)

    for route in routes:
        if not isinstance(route, dict):
            continue
        state = str(route.get("content_state", "unknown"))
        granularity = str(route.get("granularity", "unknown"))
        counts_by_granularity.setdefault(granularity, {})
        counts_by_granularity[granularity][state] = counts_by_granularity[granularity].get(state, 0) + 1

        evidence = route.get("evidence", {}) if isinstance(route.get("evidence"), dict) else {}
        note_density = _safe_float(evidence.get("note_on_density_per_second"), 0.0)
        pitch_class_count = _safe_float(evidence.get("active_pitch_classes_count"), 0.0)
        chord_confidence = _safe_float(evidence.get("chord_confidence"), 0.0)
        poly_density = _safe_float(evidence.get("polyphonic_density"), 0.0)
        metric_sums[state]["note_density"] += note_density
        metric_sums[state]["pitch_class_activity"] += pitch_class_count
        metric_sums[state]["chord_confidence"] += chord_confidence
        metric_sums[state]["polyphonic_density"] += poly_density
        metric_counts[state] += 1

        harmonic_evidence = (
            _safe_float(evidence.get("harmony_score"), 0.0) >= 0.58
            or chord_confidence >= 0.58
            or pitch_class_count >= 5
        )
        if harmonic_evidence and state not in {"harmonic_dominant", "polyphonic_full_mix", "melodic_lead"}:
            harmonic_evidence_not_harmonic.append(
                {
                    "route_id": route.get("route_id"),
                    "granularity": granularity,
                    "content_state": state,
                    "harmony_score": evidence.get("harmony_score"),
                    "rhythm_score": evidence.get("rhythm_score"),
                    "chord_confidence": chord_confidence,
                    "active_pitch_classes_count": pitch_class_count,
                    "polyphonic_density": poly_density,
                }
            )

    for decision in decisions:
        if not isinstance(decision, dict):
            continue
        state = str(decision.get("content_state", "unknown"))
        suppressed = decision.get("suppressed_labels", [])
        if isinstance(suppressed, list):
            for label in suppressed:
                label_text = str(label)
                labels_suppressed_by_state.setdefault(state, {})
                labels_suppressed_by_state[state][label_text] = labels_suppressed_by_state[state].get(label_text, 0) + 1
        evidence = decision.get("evidence", {}) if isinstance(decision.get("evidence"), dict) else {}
        if "hard_chord_label" in (suppressed if isinstance(suppressed, list) else []):
            if _safe_float(evidence.get("harmony_score"), 0.0) >= 0.62 or _safe_float(evidence.get("chord_confidence"), 0.0) >= 0.62:
                likely_false_suppressions.append(
                    {
                        "route_id": decision.get("route_id"),
                        "content_state": state,
                        "granularity": decision.get("granularity"),
                        "suppressed_labels": suppressed,
                        "harmony_score": evidence.get("harmony_score"),
                        "chord_confidence": evidence.get("chord_confidence"),
                        "active_pitch_classes_count": evidence.get("active_pitch_classes_count"),
                        "decision_margin": evidence.get("decision_margin", decision.get("decision_margin")),
                    }
                )

    avg_metrics_by_state: dict[str, dict[str, float]] = {}
    for state, count in metric_counts.items():
        count_safe = max(1, count)
        avg_metrics_by_state[state] = {
            "avg_note_density": round(metric_sums[state]["note_density"] / count_safe, 6),
            "avg_pitch_class_activity": round(metric_sums[state]["pitch_class_activity"] / count_safe, 6),
            "avg_chord_confidence": round(metric_sums[state]["chord_confidence"] / count_safe, 6),
            "avg_polyphonic_density": round(metric_sums[state]["polyphonic_density"] / count_safe, 6),
        }

    silence_examples = _top_examples(routes, "silence_or_noise", limit=10)
    percussive_examples = _top_examples(routes, "percussive_only", limit=10)
    harmonic_evidence_not_harmonic.sort(
        key=lambda row: (
            _safe_float(row.get("harmony_score"), 0.0),
            _safe_float(row.get("chord_confidence"), 0.0),
            _safe_float(row.get("active_pitch_classes_count"), 0.0),
        ),
        reverse=True,
    )

    diagnostics = {
        "performance_id": ctx["performance_id"],
        "segment_run_id": ctx["segment_run_id"],
        "created_at": now_iso(),
        "content_state_counts_by_granularity": counts_by_granularity,
        "average_metrics_by_content_state": avg_metrics_by_state,
        "silence_or_noise_examples_top_10": silence_examples,
        "percussive_only_examples_top_10": percussive_examples,
        "harmonic_evidence_not_classified_harmonic": harmonic_evidence_not_harmonic[:100],
        "labels_suppressed_by_state": labels_suppressed_by_state,
        "potential_false_suppressions": likely_false_suppressions[:100],
        "inputs_seen": {
            "route_count": len(routes),
            "routing_decision_count": len(decisions),
            "rhythm_record_count": len(rhythm_records) if isinstance(rhythm_records, list) else 0,
            "harmony_record_count": len(harmony_records) if isinstance(harmony_records, list) else 0,
            "tag_count": len(tags) if isinstance(tags, list) else 0,
            "ai_record_count": len(ai_records),
            "reliability_windows": len(reliability_payload.get("windows", []))
            if isinstance(reliability_payload.get("windows", []), list)
            else 0,
            "upgrade_candidate_count": len(upgrade_payload.get("candidates", []))
            if isinstance(upgrade_payload.get("candidates", []), list)
            else 0,
        },
    }
    diagnostics_path = routing_dir / "routing_diagnostics.json"
    save_json(diagnostics_path, diagnostics)

    report_dir = Path("reports") / "routing"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{ctx['performance_id']}_routing_diagnostics.md"
    lines = [
        f"# Routing Diagnostics - {ctx['performance_id']}",
        "",
        "## Content State Counts By Granularity",
        f"`{counts_by_granularity}`",
        "",
        "## Average Metrics By Content State",
        f"`{avg_metrics_by_state}`",
        "",
        "## Top 10 `silence_or_noise` Examples",
        f"`{silence_examples}`",
        "",
        "## Top 10 `percussive_only` Examples",
        f"`{percussive_examples}`",
        "",
        "## Harmonic Evidence Not Classified Harmonic",
        f"`{harmonic_evidence_not_harmonic[:25]}`",
        "",
        "## Labels Suppressed By State",
        f"`{labels_suppressed_by_state}`",
        "",
        "## Potential False Suppressions",
        f"`{likely_false_suppressions[:25]}`",
        "",
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return diagnostics_path.resolve(), report_path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate diagnostics for calibrated content routing decisions.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    args = parser.parse_args()
    diagnostics_path, report_path = diagnose_content_routing(Path(args.performance_manifest))
    print(f"ROUTING_DIAGNOSTICS_JSON_PATH={diagnostics_path.as_posix()}")
    print(f"ROUTING_DIAGNOSTICS_MD_PATH={report_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
