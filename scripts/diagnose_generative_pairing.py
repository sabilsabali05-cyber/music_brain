from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.feature_dataset_common import resolve_artifact_performance_dir, save_json


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:  # noqa: BLE001
        return fallback


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


def _resolve_dataset_folder(path: Path) -> Path:
    if path.exists():
        return path
    parts = list(path.parts)
    if len(parts) < 2:
        return path
    run_id = parts[-1]
    perf_id = parts[-2]
    compact_root = path.parent.parent.parent if len(parts) >= 3 else path.parent
    compact = resolve_artifact_performance_dir(compact_root, perf_id) / run_id
    return compact if compact.exists() else path


def _distribution(values: list[float]) -> dict[str, float]:
    if not values:
        return {"count": 0, "mean": 0.0, "min": 0.0, "p25": 0.0, "p50": 0.0, "p75": 0.0, "max": 0.0}
    ordered = sorted(values)

    def pct(p: float) -> float:
        idx = int(round((len(ordered) - 1) * p))
        return round(ordered[idx], 6)

    return {
        "count": len(ordered),
        "mean": round(mean(ordered), 6),
        "min": round(ordered[0], 6),
        "p25": pct(0.25),
        "p50": pct(0.5),
        "p75": pct(0.75),
        "max": round(ordered[-1], 6),
    }


def diagnose_generative_pairing(dataset_folder: Path) -> tuple[Path, Path]:
    dataset_folder = _resolve_dataset_folder(dataset_folder)
    manifest = _read_json(dataset_folder / "generative_manifest.json")
    rows = _read_jsonl(dataset_folder / "generative_examples.jsonl")

    task_counts = Counter(str(row.get("task_type", "unknown")) for row in rows)
    context_durations: list[float] = []
    target_durations: list[float] = []
    context_notes: list[float] = []
    target_notes: list[float] = []
    boundary_scores: list[float] = []
    phrase_weak_by_task = Counter()
    route_unsuitable_by_state = Counter()
    policy_fails = Counter()
    policy_fails_by_task: dict[str, Counter[str]] = defaultdict(Counter)
    dense_low_boundary_examples: list[dict[str, Any]] = []
    strict_routing_candidates: list[dict[str, Any]] = []
    near_train: list[dict[str, Any]] = []
    near_validation: list[dict[str, Any]] = []

    for row in rows:
        task_type = str(row.get("task_type", "unknown"))
        quality = row.get("quality_component_breakdown", {})
        boundary = _safe_float(quality.get("phrase_boundary_quality"), _safe_float(row.get("quality_score", {}).get("phrase_boundary_quality"), 0.0))
        target_density = _safe_float(quality.get("target_density"), _safe_float(row.get("quality_score", {}).get("target_density"), 0.0))
        final_score = _safe_float(row.get("quality_score", {}).get("final_score"), 0.0)
        reasons = [str(item) for item in row.get("split_reason_codes", []) if isinstance(item, str)]
        failed = [str(item) for item in row.get("failed_policy_checks", []) if isinstance(item, str)]
        state = str(row.get("conditioning", {}).get("content_state", "unknown")) if isinstance(row.get("conditioning"), dict) else "unknown"

        c_start = _safe_float(row.get("context_start_seconds"), 0.0)
        c_end = _safe_float(row.get("context_end_seconds"), c_start)
        t_start = _safe_float(row.get("target_start_seconds"), 0.0)
        t_end = _safe_float(row.get("target_end_seconds"), t_start)
        context_durations.append(max(0.0, c_end - c_start))
        target_durations.append(max(0.0, t_end - t_start))
        context_notes.append(_safe_float(row.get("target_summary", {}).get("context_note_count"), 0.0))
        target_notes.append(_safe_float(row.get("target_summary", {}).get("note_count"), 0.0))
        boundary_scores.append(boundary)

        if "phrase_boundary_weak" in reasons:
            phrase_weak_by_task[task_type] += 1
        if "route_state_unsuitable" in reasons:
            route_unsuitable_by_state[state] += 1
        if "task_policy_failed" in reasons or "task_policy_failed" in failed:
            policy_fails[task_type] += 1
            for check in failed or ["task_policy_failed"]:
                policy_fails_by_task[task_type][check] += 1

        if target_density >= 0.75 and boundary < 0.45:
            dense_low_boundary_examples.append(
                {
                    "example_id": row.get("example_id"),
                    "task_type": task_type,
                    "target_density": round(target_density, 6),
                    "phrase_boundary_quality": round(boundary, 6),
                    "final_score": round(final_score, 6),
                }
            )
        if "route_state_unsuitable" in reasons and task_type in {"harmony_continuation", "melody_continuation", "call_response"}:
            strict_routing_candidates.append(
                {
                    "example_id": row.get("example_id"),
                    "task_type": task_type,
                    "content_state": state,
                    "reasons": reasons[:6],
                    "boosters": row.get("quality_component_breakdown", {}).get("phrase_boundary_evidence_components", {}),
                }
            )
        if 0.68 <= final_score < 0.72:
            near_train.append(
                {
                    "example_id": row.get("example_id"),
                    "task_type": task_type,
                    "score": round(final_score, 6),
                    "split": row.get("split_recommendation"),
                    "reasons": reasons[:6],
                }
            )
        if 0.56 <= final_score < 0.60:
            near_validation.append(
                {
                    "example_id": row.get("example_id"),
                    "task_type": task_type,
                    "score": round(final_score, 6),
                    "split": row.get("split_recommendation"),
                    "reasons": reasons[:6],
                }
            )

    recommendations: list[str] = []
    if phrase_weak_by_task:
        recommendations.append("Increase phrase-like candidate generation from density/routing-change boundaries for tasks with high phrase_boundary_weak counts.")
    if route_unsuitable_by_state:
        recommendations.append("Use evidence boosters for harmony/melody/call_response when routing labels are conservative in long-form choir sections.")
    if dense_low_boundary_examples:
        recommendations.append("For dense targets with weak boundaries, expand context by one extra compatible window before excluding.")
    if near_train or near_validation:
        recommendations.append("Prioritize examples near thresholds by improving boundary evidence rather than lowering split thresholds.")
    if not recommendations:
        recommendations.append("Pairing diagnostics did not detect major pairing-pattern issues.")

    report = {
        "dataset_folder": dataset_folder.as_posix(),
        "performance_id": manifest.get("performance_id"),
        "segment_run_id": manifest.get("segment_run_id"),
        "examples_by_task_type": dict(sorted(task_counts.items())),
        "context_duration_distribution": _distribution(context_durations),
        "target_duration_distribution": _distribution(target_durations),
        "context_note_count_distribution": _distribution(context_notes),
        "target_note_count_distribution": _distribution(target_notes),
        "boundary_quality_distribution": _distribution(boundary_scores),
        "phrase_boundary_weak_by_task_type": dict(sorted(phrase_weak_by_task.items())),
        "route_state_unsuitable_by_content_state": dict(sorted(route_unsuitable_by_state.items())),
        "task_policy_failed_by_task_type": dict(sorted(policy_fails.items())),
        "task_policy_failed_by_task_and_check": {
            task: dict(sorted(counter.items())) for task, counter in sorted(policy_fails_by_task.items())
        },
        "examples_just_below_train_threshold": near_train[:50],
        "examples_just_below_validation_threshold": near_validation[:50],
        "dense_target_low_boundary_examples": dense_low_boundary_examples[:50],
        "strict_routing_candidates_for_long_form_choir": strict_routing_candidates[:50],
        "recommended_pairing_strategy_changes": recommendations,
    }

    json_path = dataset_folder / "generative_pairing_diagnostics.json"
    md_path = dataset_folder / "generative_pairing_diagnostics.md"
    save_json(json_path, report)

    lines = [
        f"# Generative Pairing Diagnostics - {dataset_folder.name}",
        "",
        "## Examples by task type",
    ]
    for task, count in report["examples_by_task_type"].items():
        lines.append(f"- {task}: `{count}`")
    lines.extend(
        [
            "",
            "## Boundary quality distribution",
            f"- `{json.dumps(report['boundary_quality_distribution'], ensure_ascii=True)}`",
            "",
            "## Phrase boundary weak by task",
            f"- `{json.dumps(report['phrase_boundary_weak_by_task_type'], ensure_ascii=True)}`",
            "",
            "## Route-state unsuitable by content state",
            f"- `{json.dumps(report['route_state_unsuitable_by_content_state'], ensure_ascii=True)}`",
            "",
            "## Recommended pairing strategy changes",
        ]
    )
    for item in recommendations:
        lines.append(f"- {item}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path.resolve(), md_path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose context/target generative pairing quality.")
    parser.add_argument("generative_dataset_folder", help="Path to a generative dataset folder")
    args = parser.parse_args()
    json_path, md_path = diagnose_generative_pairing(Path(args.generative_dataset_folder))
    print(f"GENERATIVE_PAIRING_DIAGNOSTICS_JSON={json_path.as_posix()}")
    print(f"GENERATIVE_PAIRING_DIAGNOSTICS_MD={md_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

