from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from mido import Message, MetaMessage, MidiFile, MidiTrack, second2tick, tick2second


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:  # noqa: BLE001
        return fallback


def _safe_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(value)
    except Exception:  # noqa: BLE001
        return fallback


def _clamp_midi_note(note: int) -> int:
    return max(0, min(127, note))


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


def _load_note_events_from_midi(midi_path: Path) -> list[dict[str, float]]:
    if not midi_path.exists():
        return []
    try:
        midi = MidiFile(str(midi_path))
    except Exception:  # noqa: BLE001
        return []

    events: list[dict[str, float]] = []
    tempo = 500000
    now_sec = 0.0
    active: dict[tuple[int, int], list[tuple[float, int]]] = {}

    for message in midi:
        now_sec += tick2second(message.time, midi.ticks_per_beat, tempo)
        if message.type == "set_tempo":
            tempo = int(getattr(message, "tempo", tempo))
            continue
        if message.type == "note_on" and int(getattr(message, "velocity", 0)) > 0:
            key = (int(getattr(message, "channel", 0)), int(getattr(message, "note", 0)))
            active.setdefault(key, []).append((now_sec, int(getattr(message, "velocity", 0))))
            continue
        if message.type in {"note_off", "note_on"}:
            key = (int(getattr(message, "channel", 0)), int(getattr(message, "note", 0)))
            queue = active.get(key, [])
            if not queue:
                continue
            start_sec, velocity = queue.pop(0)
            if not queue:
                active.pop(key, None)
            end_sec = max(start_sec + 1e-4, now_sec)
            events.append(
                {
                    "start": round(start_sec, 6),
                    "end": round(end_sec, 6),
                    "note": float(key[1]),
                    "velocity": float(velocity),
                }
            )
    return sorted(events, key=lambda item: item["start"])


def _extract_target_events(row: dict[str, Any]) -> tuple[list[dict[str, float]], str]:
    target_rep = row.get("target_representation", {})
    if isinstance(target_rep, dict) and isinstance(target_rep.get("midi_events"), list):
        events: list[dict[str, float]] = []
        for event in target_rep.get("midi_events", []):
            if not isinstance(event, dict):
                continue
            start = _safe_float(event.get("start"), -1.0)
            end = _safe_float(event.get("end"), -1.0)
            note = _safe_int(event.get("note"), -1)
            velocity = _safe_int(event.get("velocity"), 64)
            if start < 0 or end <= start or note < 0:
                continue
            events.append(
                {
                    "start": round(start, 6),
                    "end": round(end, 6),
                    "note": float(_clamp_midi_note(note)),
                    "velocity": float(max(1, min(127, velocity))),
                }
            )
        if events:
            return sorted(events, key=lambda item: item["start"]), "target_representation.midi_events"

    target_midi_ref = str(row.get("target_midi_ref") or "").strip()
    if target_midi_ref:
        loaded = _load_note_events_from_midi(Path(target_midi_ref))
        if loaded:
            return loaded, "target_midi_ref"
    return [], "none"


def _event_duration(events: list[dict[str, float]]) -> float:
    if not events:
        return 0.0
    return max(0.0, max(event["end"] for event in events) - min(event["start"] for event in events))


def _normalize_start(events: list[dict[str, float]]) -> list[dict[str, float]]:
    if not events:
        return []
    offset = min(event["start"] for event in events)
    return [
        {
            "start": round(max(0.0, event["start"] - offset), 6),
            "end": round(max(0.0, event["end"] - offset), 6),
            "note": event["note"],
            "velocity": event["velocity"],
        }
        for event in events
    ]


def _mode_direct_target(events: list[dict[str, float]]) -> tuple[list[dict[str, float]], str]:
    return events, "direct_target"


def _mode_transpose(events: list[dict[str, float]], semitones: int) -> tuple[list[dict[str, float]], str]:
    updated = []
    for event in events:
        updated.append(
            {
                **event,
                "note": float(_clamp_midi_note(int(round(event["note"])) + semitones)),
            }
        )
    return updated, f"transpose_{semitones:+d}"


def _mode_density_slice(events: list[dict[str, float]], nth: int, velocity_threshold: int) -> tuple[list[dict[str, float]], str]:
    nth = max(1, nth)
    sliced: list[dict[str, float]] = []
    for idx, event in enumerate(events):
        keep_idx = idx % nth == 0
        keep_vel = int(round(event["velocity"])) >= velocity_threshold
        if keep_idx and keep_vel:
            sliced.append(event)
    return sliced, f"density_slice_n{nth}_vel{velocity_threshold}"


def _mode_hybrid_context_target(row: dict[str, Any], events: list[dict[str, float]]) -> tuple[list[dict[str, float]], str | None]:
    context_start = _safe_float(row.get("context_start_seconds"), -1.0)
    context_end = _safe_float(row.get("context_end_seconds"), -1.0)
    target_start = _safe_float(row.get("target_start_seconds"), -1.0)
    target_end = _safe_float(row.get("target_end_seconds"), -1.0)
    context_duration = context_end - context_start
    target_duration = target_end - target_start
    if context_duration <= 0 or target_duration <= 0 or not events:
        return [], "hybrid_context_target_unavailable"
    scale = context_duration / max(1e-6, target_duration)
    out: list[dict[str, float]] = []
    for event in events:
        rel_start = max(0.0, event["start"] - target_start)
        rel_end = max(rel_start + 1e-4, event["end"] - target_start)
        out.append(
            {
                **event,
                "start": round(rel_start * scale, 6),
                "end": round(rel_end * scale, 6),
            }
        )
    return out, "hybrid_context_target_scaled"


def _apply_mode(
    *,
    row: dict[str, Any],
    events: list[dict[str, float]],
    mode: str,
    transpose_semitones: int,
    density_nth: int,
    density_velocity_threshold: int,
) -> tuple[list[dict[str, float]], str | None]:
    if mode == "direct_target":
        return _mode_direct_target(events)
    if mode == "transpose":
        return _mode_transpose(events, transpose_semitones)
    if mode == "density_slice":
        return _mode_density_slice(events, density_nth, density_velocity_threshold)
    if mode == "hybrid_context_target":
        return _mode_hybrid_context_target(row, events)
    return [], "unsupported_mode"


def _tempo_from_row(row: dict[str, Any]) -> int:
    conditioning = row.get("conditioning", {})
    if not isinstance(conditioning, dict):
        conditioning = {}
    tempo_context = conditioning.get("tempo_context", {})
    if not isinstance(tempo_context, dict):
        tempo_context = {}
    bpm = _safe_float(tempo_context.get("local_tempo_bpm_median"), 120.0)
    if bpm <= 0:
        bpm = 120.0
    return max(1, int(round(60_000_000.0 / bpm)))


def _write_midi(path: Path, events: list[dict[str, float]], tempo: int) -> None:
    midi = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    midi.tracks.append(track)
    track.append(MetaMessage("set_tempo", tempo=tempo, time=0))

    timeline: list[tuple[float, Message]] = []
    for event in events:
        note = _clamp_midi_note(int(round(event["note"])))
        velocity = max(1, min(127, int(round(event["velocity"]))))
        start = _safe_float(event.get("start"), 0.0)
        end = max(start + 1e-4, _safe_float(event.get("end"), start + 1e-4))
        timeline.append((start, Message("note_on", note=note, velocity=velocity, time=0)))
        timeline.append((end, Message("note_off", note=note, velocity=0, time=0)))

    timeline.sort(key=lambda item: (item[0], 0 if item[1].type == "note_off" else 1))
    prev_time = 0.0
    for event_time, msg in timeline:
        delta = max(0.0, event_time - prev_time)
        delta_ticks = int(round(second2tick(delta, midi.ticks_per_beat, tempo)))
        track.append(msg.copy(time=max(0, delta_ticks)))
        prev_time = event_time
    track.append(MetaMessage("end_of_track", time=0))

    path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(str(path))


def _split_order(split: str, split_mode: str) -> int:
    if split_mode == "validation":
        if split == "train":
            return 0
        if split == "validation":
            return 1
    return 0


def generate_midi_from_examples(
    generative_dataset_folder: Path,
    *,
    task: str,
    split: str,
    count: int,
    mode: str,
    transpose_semitones: int,
    density_nth: int,
    density_velocity_threshold: int,
    normalize_start: bool,
) -> tuple[Path, Path, Path]:
    dataset_dir = generative_dataset_folder.resolve()
    manifest_path = dataset_dir / "generative_manifest.json"
    examples_path = dataset_dir / "generative_examples.jsonl"
    if not examples_path.exists():
        raise FileNotFoundError(f"Missing generative examples: {examples_path.as_posix()}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    examples = _read_jsonl(examples_path)
    requested_split = split.strip().lower()
    split_filter = {"train"} if requested_split == "train" else {"train", "validation"} if requested_split == "validation" else {requested_split}
    selected_pool = [
        row
        for row in examples
        if str(row.get("task_type", "")).strip().lower() == task.strip().lower()
        and str(row.get("split_recommendation", "")).strip().lower() in split_filter
    ]
    selected_pool.sort(
        key=lambda row: (
            _split_order(str(row.get("split_recommendation", "")).strip().lower(), requested_split),
            -_safe_float(row.get("quality_score", {}).get("final_score"), 0.0),
        )
    )
    selected = selected_pool[: max(0, count)]

    performance_id = str(manifest.get("performance_id") or dataset_dir.parent.name)
    segment_run_id = str(manifest.get("segment_run_id") or dataset_dir.name)
    output_dir = (Path("outputs") / "generated_midi" / performance_id / segment_run_id).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    generated_files: list[str] = []
    generated_entries: list[dict[str, Any]] = []
    skipped_entries: list[dict[str, Any]] = []

    for rank, row in enumerate(selected, start=1):
        source_events, source_kind = _extract_target_events(row)
        if not source_events:
            skipped_entries.append(
                {
                    "example_id": str(row.get("example_id", "")),
                    "reason": "missing_target_events",
                    "source_event_type": source_kind,
                }
            )
            continue
        transformed, mode_note = _apply_mode(
            row=row,
            events=source_events,
            mode=mode,
            transpose_semitones=transpose_semitones,
            density_nth=density_nth,
            density_velocity_threshold=density_velocity_threshold,
        )
        if not transformed:
            skipped_entries.append(
                {
                    "example_id": str(row.get("example_id", "")),
                    "reason": "mode_produced_no_events",
                    "mode_note": mode_note,
                }
            )
            continue
        if normalize_start:
            transformed = _normalize_start(transformed)
        transformed = [event for event in transformed if event["end"] > event["start"]]
        if not transformed:
            skipped_entries.append(
                {
                    "example_id": str(row.get("example_id", "")),
                    "reason": "empty_after_normalization",
                    "mode_note": mode_note,
                }
            )
            continue
        file_name = f"generated_{task}_{rank}.mid"
        midi_path = output_dir / file_name
        tempo = _tempo_from_row(row)
        _write_midi(midi_path, transformed, tempo)
        generated_files.append(midi_path.as_posix())
        generated_entries.append(
            {
                "example_id": str(row.get("example_id", "")),
                "task_type": str(row.get("task_type", "")),
                "split_recommendation": str(row.get("split_recommendation", "")),
                "quality_score": _safe_float(row.get("quality_score", {}).get("final_score"), 0.0),
                "mode": mode,
                "mode_note": mode_note,
                "source_event_type": source_kind,
                "target_midi_ref": str(row.get("target_midi_ref") or ""),
                "context_midi_ref": str(row.get("context_midi_ref") or ""),
                "output_midi_path": midi_path.as_posix(),
                "source_note_count": len(source_events),
                "generated_note_count": len(transformed),
                "generated_duration_seconds": round(_event_duration(transformed), 6),
                "provenance": {
                    "prototype_generated_from_existing_examples": True,
                    "not_original_model_composition": True,
                    "not_ground_truth": True,
                    "model_trained_output": False,
                    "weak_labels_promoted_to_ground_truth": False,
                },
            }
        )

    report = {
        "status": "success",
        "generative_dataset_folder": dataset_dir.as_posix(),
        "performance_id": performance_id,
        "segment_run_id": segment_run_id,
        "selection": {
            "task": task,
            "split": requested_split,
            "count_requested": count,
            "count_selected": len(selected),
            "count_generated": len(generated_entries),
            "mode": mode,
        },
        "provenance_notice": {
            "prototype_generated_from_existing_examples": True,
            "not_original_model_composition": True,
            "not_ground_truth": True,
            "model_trained_output": False,
        },
        "generated_files": generated_files,
        "generated_examples": generated_entries,
        "skipped_examples": skipped_entries,
    }

    report_path = output_dir / "generation_report.json"
    summary_path = output_dir / "generation_summary.md"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    lines = [
        "# Prototype MIDI Generation Summary",
        "",
        f"- performance_id: `{performance_id}`",
        f"- segment_run_id: `{segment_run_id}`",
        f"- task: `{task}`",
        f"- split: `{requested_split}`",
        f"- mode: `{mode}`",
        f"- requested count: `{count}`",
        f"- generated count: `{len(generated_entries)}`",
        f"- skipped count: `{len(skipped_entries)}`",
        "- provenance: `prototype_generated_from_existing_examples`",
        "- composition_claim: `not_original_model_composition`",
        "- ground_truth_claim: `not_ground_truth`",
        "",
        "## Generated files",
    ]
    if generated_entries:
        for entry in generated_entries:
            lines.append(
                f"- `{Path(str(entry['output_midi_path'])).name}` from `{entry['example_id']}` "
                f"(split `{entry['split_recommendation']}`, quality `{entry['quality_score']}`)"
            )
    else:
        lines.append("- none")
    if skipped_entries:
        lines.extend(["", "## Skipped examples"])
        for entry in skipped_entries:
            lines.append(f"- `{entry.get('example_id', '')}`: `{entry.get('reason', '')}`")
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return output_dir, report_path, summary_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate prototype MIDI sketches from existing generative examples.")
    parser.add_argument("generative_dataset_folder", help="Path to generative dataset folder")
    parser.add_argument("--task", default="continuation", help="Task type filter")
    parser.add_argument("--split", default="train", help="Split filter (train or validation recommended)")
    parser.add_argument("--count", type=int, default=4, help="Number of examples to generate")
    parser.add_argument(
        "--mode",
        default="direct_target",
        choices=["direct_target", "transpose", "density_slice", "hybrid_context_target"],
        help="Prototype generation mode",
    )
    parser.add_argument("--transpose-semitones", type=int, default=2, help="Semitone shift used by transpose mode")
    parser.add_argument("--density-nth", type=int, default=2, help="Keep every nth note in density_slice mode")
    parser.add_argument("--density-velocity-threshold", type=int, default=1, help="Velocity threshold for density_slice mode")
    parser.add_argument("--no-normalize-start", action="store_true", help="Do not normalize first note start to 0")
    args = parser.parse_args()

    output_dir, report_path, summary_path = generate_midi_from_examples(
        Path(args.generative_dataset_folder),
        task=args.task,
        split=args.split,
        count=args.count,
        mode=args.mode,
        transpose_semitones=args.transpose_semitones,
        density_nth=args.density_nth,
        density_velocity_threshold=args.density_velocity_threshold,
        normalize_start=not args.no_normalize_start,
    )
    print(f"GENERATED_MIDI_OUTPUT_DIR={output_dir.as_posix()}")
    print(f"GENERATION_REPORT_JSON={report_path.as_posix()}")
    print(f"GENERATION_SUMMARY_MD={summary_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
