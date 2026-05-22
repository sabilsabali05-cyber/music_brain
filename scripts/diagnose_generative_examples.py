from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from mido import MidiFile, merge_tracks, tick2second

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.generative.task_policies import SPLIT_THRESHOLDS, TASK_POLICIES
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
            row = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(row, dict):
            rows.append(row)
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


def _load_note_events(midi_path: Path | None) -> list[dict[str, float]]:
    if midi_path is None or not midi_path.exists():
        return []
    try:
        midi = MidiFile(midi_path.as_posix())
    except Exception:  # noqa: BLE001
        return []
    events: list[dict[str, float]] = []
    tempo = 500000
    now_sec = 0.0
    active: dict[tuple[int, int], list[tuple[float, int]]] = {}
    for message in merge_tracks(midi.tracks):
        now_sec += tick2second(message.time, midi.ticks_per_beat, tempo)
        if message.type == "set_tempo":
            tempo = int(getattr(message, "tempo", tempo))
            continue
        if message.type == "note_on" and int(getattr(message, "velocity", 0)) > 0:
            key = (int(getattr(message, "channel", 0)), int(getattr(message, "note", 0)))
            active.setdefault(key, []).append((now_sec, int(getattr(message, "velocity", 0))))
            continue
        if message.type in {"note_off", "note_on"}:
            vel = int(getattr(message, "velocity", 0))
            if message.type == "note_on" and vel > 0:
                continue
            key = (int(getattr(message, "channel", 0)), int(getattr(message, "note", 0)))
            queue = active.get(key, [])
            if not queue:
                continue
            start, velocity = queue.pop(0)
            if not queue:
                active.pop(key, None)
            events.append({"start": start, "end": max(start + 1e-4, now_sec), "note": float(key[1]), "velocity": float(velocity)})
    return sorted(events, key=lambda item: item["start"])


def _events_in_range(events: list[dict[str, float]], start_seconds: float, end_seconds: float) -> list[dict[str, float]]:
    return [event for event in events if not (event["end"] < start_seconds or event["start"] > end_seconds)]


def diagnose_generative_examples(dataset_folder: Path) -> tuple[Path, Path]:
    dataset_folder = _resolve_dataset_folder(dataset_folder)
    manifest_path = dataset_folder / "generative_manifest.json"
    jsonl_path = dataset_folder / "generative_examples.jsonl"
    manifest = _read_json(manifest_path)
    rows = _read_jsonl(jsonl_path)

    split_reasons: dict[str, Counter[str]] = {
        "train": Counter(),
        "validation": Counter(),
        "review": Counter(),
        "exclude": Counter(),
    }
    quality_keys = [
        "transcription_reliability",
        "route_suitability",
        "phrase_boundary_quality",
        "target_density",
        "musical_completeness",
        "repetition_or_motif_strength",
        "witness_agreement_score",
        "ambiguity_penalty",
        "review_penalty",
        "final_score",
    ]
    quality_values: dict[str, list[float]] = {key: [] for key in quality_keys}
    per_task: dict[str, dict[str, Any]] = {}

    for row in rows:
        split = str(row.get("split_recommendation", "review"))
        reasons = row.get("split_reason_codes", [])
        if isinstance(reasons, list):
            for reason in reasons:
                split_reasons.setdefault(split, Counter())[str(reason)] += 1
        quality = row.get("quality_score", {})
        for key in quality_keys:
            quality_values[key].append(_safe_float(quality.get(key), 0.0))

        task = str(row.get("task_type", "unknown"))
        task_stats = per_task.setdefault(
            task,
            {
                "count": 0,
                "scores": [],
                "splits": Counter(),
                "exclude_reasons": Counter(),
                "missing_refs": Counter(),
                "target_note_counts": [],
                "context_note_counts": [],
            },
        )
        task_stats["count"] += 1
        task_stats["scores"].append(_safe_float(quality.get("final_score"), 0.0))
        task_stats["splits"][split] += 1
        if split == "exclude" and isinstance(reasons, list):
            for reason in reasons:
                task_stats["exclude_reasons"][str(reason)] += 1
        for ref in row.get("missing_refs", []) if isinstance(row.get("missing_refs"), list) else []:
            task_stats["missing_refs"][str(ref)] += 1
        task_stats["target_note_counts"].append(
            int(row.get("target_summary", {}).get("note_count", 0)) if isinstance(row.get("target_summary"), dict) else 0
        )
        task_stats["context_note_counts"].append(
            int(row.get("target_summary", {}).get("context_note_count", 0)) if isinstance(row.get("target_summary"), dict) else 0
        )

    salvage_rows = [
        row
        for row in rows
        if str(row.get("split_recommendation", "")) in {"review", "exclude"}
    ]
    salvage_rows.sort(
        key=lambda row: _safe_float(row.get("quality_score", {}).get("final_score"), 0.0),
        reverse=True,
    )
    top_salvage = []
    for row in salvage_rows[:25]:
        blockers = sorted(
            set(
                [str(item) for item in row.get("split_reason_codes", []) if isinstance(item, str)]
                + [str(item) for item in row.get("failed_policy_checks", []) if isinstance(item, str)]
                + [str(item) for item in row.get("missing_refs", []) if isinstance(item, str)]
            )
        )
        needs = []
        score = _safe_float(row.get("quality_score", {}).get("final_score"), 0.0)
        if score < SPLIT_THRESHOLDS["validation"]:
            needs.append("increase final_score into validation/train threshold")
        if "target_too_sparse" in blockers or "no_target_events" in blockers:
            needs.append("target region needs denser note events")
        if "low_transcription_reliability" in blockers:
            needs.append("higher transcription reliability evidence")
        if "task_policy_failed" in blockers:
            needs.append("task-policy compatible context/target routing")
        top_salvage.append(
            {
                "example_id": row.get("example_id"),
                "task_type": row.get("task_type"),
                "final_score": score,
                "current_split": row.get("split_recommendation"),
                "blockers": blockers,
                "what_would_need_to_improve": needs,
            }
        )

    source_feature_dir = Path(str(manifest.get("source_feature_dir", ""))) if manifest.get("source_feature_dir") else None
    harmony_diag = {
        "harmonic_or_polyphonic_regions_available": 0,
        "regions_with_pitch_harmony_refs": 0,
        "regions_with_target_midi_events": 0,
        "why_no_examples_were_created": [],
    }
    motif_diag = {
        "motif_candidates_available": 0,
        "repeated_motif_groups": 0,
        "passing_duration_note_constraints": 0,
        "why_no_examples_were_created": [],
    }
    if source_feature_dir and source_feature_dir.exists():
        routes_payload = _read_json(source_feature_dir / "routing" / "content_region_routes.json")
        routes = routes_payload.get("routes", []) if isinstance(routes_payload.get("routes"), list) else []
        harmony_regions = [
            row for row in routes if isinstance(row, dict) and str(row.get("content_state")) in {"harmonic_dominant", "polyphonic_full_mix"}
        ]
        harmony_diag["harmonic_or_polyphonic_regions_available"] = len(harmony_regions)
        pitch_harmony_path = source_feature_dir / "pitch_harmony" / "pitch_harmony_features.json"
        if pitch_harmony_path.exists():
            harmony_diag["regions_with_pitch_harmony_refs"] = len(harmony_regions)
        merged_midi = Path(str(manifest.get("source_merged_midi_ref", ""))) if manifest.get("source_merged_midi_ref") else None
        events = _load_note_events(merged_midi)
        for region in harmony_regions:
            r_events = _events_in_range(events, _safe_float(region.get("start_seconds"), 0.0), _safe_float(region.get("end_seconds"), 0.0))
            if r_events:
                harmony_diag["regions_with_target_midi_events"] += 1
        if not any(str(row.get("task_type")) == "harmony_continuation" for row in rows):
            if harmony_diag["harmonic_or_polyphonic_regions_available"] == 0:
                harmony_diag["why_no_examples_were_created"].append("no harmonic/polyphonic regions in routing")
            if harmony_diag["regions_with_target_midi_events"] == 0:
                harmony_diag["why_no_examples_were_created"].append("harmonic/polyphonic regions had no target events")

        rhythm_payload = _read_json(source_feature_dir / "rhythm_features.json")
        motifs = rhythm_payload.get("rhythm_motifs", {})
        motif_list = motifs.get("motifs", []) if isinstance(motifs, dict) and isinstance(motifs.get("motifs"), list) else []
        motif_groups = rhythm_payload.get("rhythm_motif_groups", []) if isinstance(rhythm_payload.get("rhythm_motif_groups"), list) else []
        motif_diag["motif_candidates_available"] = len(motif_list)
        repeated_groups = [group for group in motif_groups if isinstance(group, dict) and len(group.get("window_ids", [])) >= 2]
        motif_diag["repeated_motif_groups"] = len(repeated_groups)
        policy = TASK_POLICIES.get("motif_transformation", {})
        min_duration = _safe_float(policy.get("minimum_duration"), 0.0)
        min_notes = int(policy.get("minimum_note_count", 1))
        for group in repeated_groups:
            window_ids = [str(item) for item in group.get("window_ids", []) if isinstance(item, str)]
            if len(window_ids) < 2:
                continue
            if not source_feature_dir:
                continue
            seg_manifest = _read_json(Path(str(manifest.get("source_segments_manifest", ""))))
            windows = seg_manifest.get("transcription_windows", []) if isinstance(seg_manifest.get("transcription_windows"), list) else []
            by_id = {str(window.get("window_id")): window for window in windows if isinstance(window, dict)}
            src = by_id.get(window_ids[0])
            tgt = by_id.get(window_ids[1])
            if not src or not tgt:
                continue
            start = _safe_float(tgt.get("core_start_seconds"), 0.0)
            end = _safe_float(tgt.get("core_end_seconds"), 0.0)
            target_events = _events_in_range(events, start, end)
            if end - start >= min_duration and len(target_events) >= min_notes:
                motif_diag["passing_duration_note_constraints"] += 1
        if not any(str(row.get("task_type")) == "motif_transformation" for row in rows):
            if motif_diag["motif_candidates_available"] == 0:
                motif_diag["why_no_examples_were_created"].append("no motif candidates")
            if motif_diag["repeated_motif_groups"] == 0:
                motif_diag["why_no_examples_were_created"].append("no repeated motif groups")
            if motif_diag["passing_duration_note_constraints"] == 0:
                motif_diag["why_no_examples_were_created"].append("no repeated groups passing duration/note constraints")

    report = {
        "dataset_folder": dataset_folder.as_posix(),
        "example_count": len(rows),
        "split_reason_breakdown": {
            split: dict(sorted(counter.items())) for split, counter in split_reasons.items()
        },
        "quality_component_stats": {
            key: round(mean(values), 6) if values else 0.0 for key, values in quality_values.items()
        },
        "per_task_stats": {
            task: {
                "count": stats["count"],
                "average_score": round(mean(stats["scores"]), 6) if stats["scores"] else 0.0,
                "split_counts": dict(sorted(stats["splits"].items())),
                "top_exclusion_reason": stats["exclude_reasons"].most_common(1)[0][0] if stats["exclude_reasons"] else None,
                "missing_required_refs": dict(sorted(stats["missing_refs"].items())),
                "average_target_note_count": round(mean(stats["target_note_counts"]), 6) if stats["target_note_counts"] else 0.0,
                "average_context_note_count": round(mean(stats["context_note_counts"]), 6) if stats["context_note_counts"] else 0.0,
            }
            for task, stats in sorted(per_task.items())
        },
        "top_salvage_candidates": top_salvage,
        "missing_task_diagnostics": {
            "harmony_continuation": harmony_diag,
            "motif_transformation": motif_diag,
        },
    }

    json_out = dataset_folder / "generative_quality_diagnostics.json"
    md_out = dataset_folder / "generative_quality_diagnostics.md"
    save_json(json_out, report)

    lines = [
        f"# Generative Quality Diagnostics - {dataset_folder.name}",
        "",
        f"- example_count: `{len(rows)}`",
        "",
        "## Split reason breakdown",
    ]
    for split, counts in report["split_reason_breakdown"].items():
        lines.append(f"- {split}: `{json.dumps(counts, ensure_ascii=True)}`")
    lines.extend(["", "## Quality component averages"])
    for key, value in report["quality_component_stats"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Missing task diagnostics"])
    lines.append(f"- harmony_continuation: `{json.dumps(harmony_diag, ensure_ascii=True)}`")
    lines.append(f"- motif_transformation: `{json.dumps(motif_diag, ensure_ascii=True)}`")
    lines.extend(["", "## Top salvage candidates"])
    for item in top_salvage[:25]:
        lines.append(
            "- "
            + json.dumps(
                {
                    "example_id": item["example_id"],
                    "task_type": item["task_type"],
                    "final_score": item["final_score"],
                    "current_split": item["current_split"],
                    "blockers": item["blockers"][:5],
                },
                ensure_ascii=True,
            )
        )
    md_out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_out.resolve(), md_out.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose generative example split/quality outcomes.")
    parser.add_argument("generative_dataset_folder", help="Path to a generative dataset folder")
    args = parser.parse_args()
    json_path, md_path = diagnose_generative_examples(Path(args.generative_dataset_folder))
    print(f"GENERATIVE_DIAGNOSTICS_JSON={json_path.as_posix()}")
    print(f"GENERATIVE_DIAGNOSTICS_MD={md_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

