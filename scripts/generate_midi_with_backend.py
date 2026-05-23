from __future__ import annotations

import argparse
import importlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from mido import Message, MidiFile, MidiTrack, second2tick

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.symbolic_models.backends.registry import get_symbolic_model_provider
from features.symbolic_models.model_backend_schema import SymbolicGenerationRequest


def _read_json(path: Path) -> dict[str, Any]:
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


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:  # noqa: BLE001
        return fallback


def _write_midi_from_events(output_path: Path, events: list[dict[str, Any]]) -> int:
    midi = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    midi.tracks.append(track)
    timeline: list[tuple[float, Message]] = []
    for row in events:
        if not isinstance(row, dict):
            continue
        start = _safe_float(row.get("start"), -1.0)
        end = _safe_float(row.get("end"), -1.0)
        note = int(_safe_float(row.get("note"), -1.0))
        velocity = int(_safe_float(row.get("velocity"), 64.0))
        if start < 0 or end <= start or note < 0:
            continue
        note = max(0, min(127, note))
        velocity = max(1, min(127, velocity))
        timeline.append((start, Message("note_on", note=note, velocity=velocity, time=0)))
        timeline.append((end, Message("note_off", note=note, velocity=0, time=0)))
    timeline.sort(key=lambda item: (item[0], 0 if item[1].type == "note_off" else 1))
    if not timeline:
        return 0
    offset = timeline[0][0]
    previous_seconds = 0.0
    note_on_count = 0
    for at_seconds, message in timeline:
        normalized = max(0.0, at_seconds - offset)
        delta_seconds = max(0.0, normalized - previous_seconds)
        delta_ticks = int(round(second2tick(delta_seconds, midi.ticks_per_beat, 500000)))
        track.append(message.copy(time=max(0, delta_ticks)))
        previous_seconds = normalized
        if message.type == "note_on" and int(getattr(message, "velocity", 0)) > 0:
            note_on_count += 1
    output_path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(output_path.as_posix())
    return note_on_count


def _fallback_example_retrieval(dataset_folder: Path, output_dir: Path, task: str, split: str) -> dict[str, Any]:
    examples = _read_jsonl(dataset_folder / "generative_examples.jsonl")
    split_order = {"train": 0, "validation": 1, "review": 2, "exclude": 3}
    allowed_splits = {"train"} if split == "train" else {"train", "validation"}
    selected = [
        row
        for row in examples
        if str(row.get("task_type", "")).strip().lower() == task.strip().lower()
        and str(row.get("split_recommendation", "")).strip().lower() in allowed_splits
    ]
    selected.sort(
        key=lambda row: (
            split_order.get(str(row.get("split_recommendation", "")).strip().lower(), 9),
            -_safe_float(row.get("quality_score", {}).get("final_score"), 0.0),
        )
    )
    selected = selected[:4]
    output_files: list[str] = []
    input_examples: list[str] = []
    for idx, row in enumerate(selected, start=1):
        events = []
        target_representation = row.get("target_representation", {})
        if isinstance(target_representation, dict) and isinstance(target_representation.get("midi_events"), list):
            events = target_representation.get("midi_events", [])
        out_path = output_dir / f"generated_{task}_{idx}.mid"
        note_count = _write_midi_from_events(out_path, events)
        if note_count <= 0:
            continue
        output_files.append(out_path.as_posix())
        input_examples.append(str(row.get("example_id", "")))
    return {"output_files": output_files, "input_examples": input_examples}


def _copy_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _build_run_output_dir(provider_id: str, performance_id: str, segment_run_id: str) -> Path:
    return (Path("outputs") / "model_backend_runs" / provider_id / performance_id / segment_run_id).resolve()


def _write_run_report(output_dir: Path, payload: dict[str, Any]) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "model_backend_run_report.json"
    summary_path = output_dir / "model_backend_run_summary.md"
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    lines = [
        "# Model Backend Run Summary",
        "",
        f"- provider_id: `{payload.get('provider_id', '')}`",
        f"- availability: `{payload.get('availability', False)}`",
        f"- task: `{payload.get('task', '')}`",
        f"- prompt: `{payload.get('prompt', '')}`",
        f"- generation_status: `{payload.get('generation_status', '')}`",
        f"- limitations: `{payload.get('limitations', [])}`",
        f"- provenance: `{payload.get('provenance', {})}`",
        "",
        "## Input examples used",
    ]
    input_examples = payload.get("input_examples_used", [])
    if isinstance(input_examples, list) and input_examples:
        for item in input_examples:
            lines.append(f"- `{item}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Output files"])
    output_files = payload.get("output_files", [])
    if isinstance(output_files, list) and output_files:
        for item in output_files:
            lines.append(f"- `{item}`")
    else:
        lines.append("- none")
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path, summary_path


def generate_midi_with_backend(
    dataset_folder: Path,
    *,
    provider: str,
    task: str,
    prompt: str | None = None,
    split: str = "train",
) -> tuple[Path, Path, Path]:
    dataset_folder = dataset_folder.resolve()
    manifest = _read_json(dataset_folder / "generative_manifest.json")
    performance_id = str(manifest.get("performance_id") or dataset_folder.parent.name)
    segment_run_id = str(manifest.get("segment_run_id") or dataset_folder.name)
    provider_id = provider.strip().lower()
    output_dir = _build_run_output_dir(provider_id, performance_id, segment_run_id)

    if provider_id == "example_retrieval":
        try:
            generator_module = importlib.import_module("scripts.generate_midi_from_examples")
            generate_midi_from_examples = getattr(generator_module, "generate_midi_from_examples")
        except Exception as exc:  # noqa: BLE001
            fallback = _fallback_example_retrieval(dataset_folder, output_dir, task, split)
            run_payload = {
                "provider_id": provider_id,
                "availability": True if fallback["output_files"] else False,
                "task": task,
                "prompt": prompt,
                "input_examples_used": fallback["input_examples"],
                "conditioning_fields": ["task_type", "split_recommendation", "quality_score", "target_representation"],
                "generation_status": "success_internal_example_fallback" if fallback["output_files"] else "unavailable",
                "limitations": [f"Delegation module unavailable: {exc}", "Used internal fallback path from existing examples."],
                "output_files": fallback["output_files"],
                "provenance": {
                    "prototype_generated_from_existing_examples": True,
                    "not_original_model_composition": True,
                    "not_ground_truth": True,
                    "not_model_trained": True,
                },
            }
            report_path, summary_path = _write_run_report(output_dir, run_payload)
            return output_dir, report_path, summary_path

        source_output_dir, source_report, source_summary = generate_midi_from_examples(
            dataset_folder,
            task=task,
            split=split,
            count=4,
            mode="direct_target",
            transpose_semitones=2,
            density_nth=2,
            density_velocity_threshold=1,
            normalize_start=True,
        )
        output_files: list[str] = []
        for midi_path in sorted(source_output_dir.glob("generated_*.mid")):
            copied = output_dir / midi_path.name
            _copy_if_exists(midi_path, copied)
            output_files.append(copied.as_posix())
        copied_source_report = output_dir / "delegated_generation_report.json"
        copied_source_summary = output_dir / "delegated_generation_summary.md"
        _copy_if_exists(source_report, copied_source_report)
        _copy_if_exists(source_summary, copied_source_summary)

        source_payload = _read_json(source_report)
        run_payload = {
            "provider_id": provider_id,
            "availability": True,
            "task": task,
            "prompt": prompt,
            "input_examples_used": [item.get("example_id") for item in source_payload.get("generated_examples", []) if isinstance(item, dict)],
            "conditioning_fields": ["task_type", "split_recommendation", "quality_score", "target_representation"],
            "generation_status": "success_delegated_to_example_retrieval",
            "limitations": ["Delegated to existing example-based generator.", "No symbolic model backend inference executed."],
            "output_files": output_files,
            "provenance": {
                "prototype_generated_from_existing_examples": True,
                "not_original_model_composition": True,
                "not_ground_truth": True,
                "not_model_trained": True,
            },
        }
        report_path, summary_path = _write_run_report(output_dir, run_payload)
        return output_dir, report_path, summary_path

    adapter = get_symbolic_model_provider(provider_id)
    if adapter is None:
        run_payload = {
            "provider_id": provider_id,
            "availability": False,
            "task": task,
            "prompt": prompt,
            "input_examples_used": [],
            "conditioning_fields": [],
            "generation_status": "unknown_provider",
            "limitations": ["Provider is not registered."],
            "output_files": [],
            "provenance": {
                "prototype_generated_from_existing_examples": False,
                "not_original_model_composition": True,
                "not_ground_truth": True,
                "not_model_trained": True,
            },
        }
        report_path, summary_path = _write_run_report(output_dir, run_payload)
        return output_dir, report_path, summary_path

    availability = adapter.check_available()
    request = SymbolicGenerationRequest(
        provider_id=provider_id,
        generative_dataset_folder=dataset_folder.as_posix(),
        task_type=task,
        prompt=prompt,
        split=split,
    )
    result = adapter.generate_midi(request)
    run_payload = {
        "provider_id": provider_id,
        "availability": bool(availability.available),
        "task": task,
        "prompt": prompt,
        "input_examples_used": [],
        "conditioning_fields": ["task_type", "split_recommendation", "quality_score"],
        "generation_status": result.generation_status,
        "limitations": result.limitations,
        "output_files": result.output_midi_paths,
        "installation_hint": availability.installation_hint,
        "role_hint": availability.role_hint,
        "provenance": {
            "prototype_generated_from_existing_examples": False,
            "not_original_model_composition": True,
            "not_ground_truth": True,
            "not_model_trained": True,
        },
    }
    report_path, summary_path = _write_run_report(output_dir, run_payload)
    return output_dir, report_path, summary_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate MIDI sketches using symbolic backend adapters.")
    parser.add_argument("generative_dataset_folder", help="Path to generative dataset folder")
    parser.add_argument(
        "--provider",
        default="example_retrieval",
        choices=["example_retrieval", "moonbeam", "midigpt", "text2midi"],
        help="Backend provider",
    )
    parser.add_argument("--task", default="continuation", help="Task type")
    parser.add_argument("--split", default="train", help="Split for example retrieval provider")
    parser.add_argument("--prompt", default=None, help="Optional prompt")
    args = parser.parse_args()
    output_dir, report_path, summary_path = generate_midi_with_backend(
        Path(args.generative_dataset_folder),
        provider=args.provider,
        task=args.task,
        prompt=args.prompt,
        split=args.split,
    )
    print(f"MODEL_BACKEND_OUTPUT_DIR={output_dir.as_posix()}")
    print(f"MODEL_BACKEND_REPORT_JSON={report_path.as_posix()}")
    print(f"MODEL_BACKEND_SUMMARY_MD={summary_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
