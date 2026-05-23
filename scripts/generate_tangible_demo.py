from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from mido import Message, MetaMessage, MidiFile, MidiTrack, second2tick

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.tangible_generation.demo_schema import (  # noqa: E402
    DemoCompositionPlan,
    DemoGenerationReport,
    DemoMidiPart,
    DemoSection,
    DemoSoundRole,
    DemoSynplantSeedSuggestion,
)

PHI = (1.0 + math.sqrt(5.0)) / 2.0
SUPPORTED_TASKS = {
    "continuation",
    "phrase_continuation",
    "groove_continuation",
    "harmony_continuation",
    "call_response",
    "section_transition",
    "buildup_to_release",
}


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:  # noqa: BLE001
        return fallback


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


def _clamp(note: int) -> int:
    return max(0, min(127, note))


def _to_repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT_DIR.resolve()).as_posix()
    except Exception:  # noqa: BLE001
        return path.as_posix()


def _discover_examples() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((ROOT_DIR / "datasets" / "generative_training").glob("**/generative_examples.jsonl")):
        folder = path.parent
        for row in _read_jsonl(path):
            task = str(row.get("task_type", "")).strip().lower()
            split = str(row.get("split_recommendation", "")).strip().lower()
            quality = _safe_float(row.get("quality_score", {}).get("final_score"), 0.0)
            if task not in SUPPORTED_TASKS or split not in {"train", "validation"} or quality < 0.45:
                continue
            rep = row.get("target_representation", {})
            events = rep.get("midi_events", []) if isinstance(rep, dict) else []
            if not isinstance(events, list) or not events:
                continue
            rows.append({"folder": _to_repo_relative(folder), "example_id": str(row.get("example_id", "")), "task": task, "events": events, "quality": quality})
    rows.sort(key=lambda item: (-item["quality"], item["example_id"]))
    return rows


def _write_midi(path: Path, events: list[dict[str, float]], channel: int) -> int:
    midi = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    midi.tracks.append(track)
    tempo = int(round(60_000_000 / 120.0))
    track.append(MetaMessage("set_tempo", tempo=tempo, time=0))
    timeline: list[tuple[float, Message]] = []
    notes = 0
    for event in events:
        start = float(event["start"])
        end = max(start + 0.05, float(event["end"]))
        note = _clamp(int(round(float(event["note"]))))
        vel = max(1, min(127, int(round(float(event["velocity"])))))
        timeline.append((start, Message("note_on", channel=channel, note=note, velocity=vel, time=0)))
        timeline.append((end, Message("note_off", channel=channel, note=note, velocity=0, time=0)))
    timeline.sort(key=lambda x: (x[0], 0 if x[1].type == "note_off" else 1))
    prev = 0.0
    for when, msg in timeline:
        dt = int(round(second2tick(max(0.0, when - prev), midi.ticks_per_beat, tempo)))
        track.append(msg.copy(time=max(0, dt)))
        prev = when
        if msg.type == "note_on" and msg.velocity > 0:
            notes += 1
    track.append(MetaMessage("end_of_track", time=0))
    path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(str(path))
    return notes


def calculate_climax_seconds(duration: float, ratio: str) -> float:
    if ratio == "golden_ratio":
        return duration / PHI
    return duration * 0.62


def generate_tangible_demo(duration_seconds: float = 180.0, ratio: str = "golden_ratio", goal: str = "climax") -> dict[str, Any]:
    examples = _discover_examples()
    if not examples:
        raise RuntimeError("No generative examples found.")

    output_dir = ROOT_DIR / "outputs" / "tangible_generation_v1"
    output_dir.mkdir(parents=True, exist_ok=True)
    role_map = {
        "drums": ("generated_drums.mid", 9),
        "bass": ("generated_bass.mid", 1),
        "chords": ("generated_chords.mid", 2),
        "lead": ("generated_lead.mid", 3),
        "texture_bed": ("generated_texture_motifs.mid", 4),
    }
    climax_seconds = round(calculate_climax_seconds(duration_seconds, ratio), 3)
    sections = [
        DemoSection("intro", "intro", 0.0, round(duration_seconds * 0.14, 3), "establish"),
        DemoSection("build", "build", round(duration_seconds * 0.14, 3), round(climax_seconds - duration_seconds * 0.08, 3), "build"),
        DemoSection("climax", "climax", round(climax_seconds - duration_seconds * 0.08, 3), round(climax_seconds + duration_seconds * 0.06, 3), goal),
        DemoSection("release", "release", round(climax_seconds + duration_seconds * 0.06, 3), round(duration_seconds * 0.9, 3), "release"),
        DemoSection("outro", "outro", round(duration_seconds * 0.9, 3), round(duration_seconds, 3), "resolve"),
    ]

    midi_parts: list[DemoMidiPart] = []
    sound_roles: list[DemoSoundRole] = []
    track_note_counts: dict[str, int] = {}
    source_ids: list[str] = []
    transforms: list[str] = []
    merged_events: list[tuple[str, dict[str, float]]] = []
    for idx, (role, (file_name, channel)) in enumerate(role_map.items()):
        example = examples[idx % len(examples)]
        events_raw = example["events"]
        base = []
        offset = _safe_float(events_raw[0].get("start"), 0.0) if events_raw else 0.0
        for e in events_raw[:256]:
            start = max(0.0, _safe_float(e.get("start"), 0.0) - offset)
            end = max(start + 0.05, _safe_float(e.get("end"), start + 0.2) - offset)
            note = _clamp(int(_safe_float(e.get("note"), 60.0)) + ((idx % 5) - 2))
            vel = max(1, min(127, int(_safe_float(e.get("velocity"), 80.0))))
            # deterministic downsample for novelty
            if int(start * 100) % (idx + 2) != 0:
                continue
            duration_scale = 0.8 + (idx % 3) * 0.1
            base.append({"start": round(start * 0.5, 6), "end": round(end * duration_scale * 0.5, 6), "note": float(note), "velocity": float(vel)})
        midi_path = output_dir / file_name
        count = _write_midi(midi_path, base, channel)
        track_note_counts[role] = count
        source_ids.append(example["example_id"])
        transforms.append(f"{role}: transpose_{(idx % 5) - 2}, density_slice_{idx + 2}")
        midi_parts.append(
            DemoMidiPart(
                part_id=f"{role}_part",
                track_role=role,  # type: ignore[arg-type]
                source_example_ids=[example["example_id"]],
                transformations_applied=[transforms[-1]],
                note_count=count,
            )
        )
        sound_roles.append(DemoSoundRole(track_role=role, requested_texture=f"{role}_texture", generation_method="recombined_example"))  # type: ignore[arg-type]
        for evt in base:
            merged_events.append((role, evt))

    # merged song multitrack
    song_midi = MidiFile(ticks_per_beat=480)
    tempo = int(round(60_000_000 / 120.0))
    for role, (_, channel) in role_map.items():
        track = MidiTrack()
        song_midi.tracks.append(track)
        track.append(MetaMessage("track_name", name=role, time=0))
        track.append(MetaMessage("set_tempo", tempo=tempo, time=0))
        timeline = []
        for evt_role, evt in merged_events:
            if evt_role != role:
                continue
            timeline.append((evt["start"], Message("note_on", channel=channel, note=_clamp(int(evt["note"])), velocity=max(1, int(evt["velocity"])), time=0)))
            timeline.append((evt["end"], Message("note_off", channel=channel, note=_clamp(int(evt["note"])), velocity=0, time=0)))
        timeline.sort(key=lambda x: (x[0], 0 if x[1].type == "note_off" else 1))
        prev = 0.0
        for when, msg in timeline:
            dt = int(round(second2tick(max(0.0, when - prev), song_midi.ticks_per_beat, tempo)))
            track.append(msg.copy(time=max(0, dt)))
            prev = when
        track.append(MetaMessage("end_of_track", time=0))
    song_path = output_dir / "generated_song.mid"
    song_midi.save(str(song_path))
    track_note_counts["song"] = sum(track_note_counts.values())

    plan = DemoCompositionPlan(
        plan_id="tangible_generation_v1_plan",
        duration_seconds=duration_seconds,
        structure_ratio=ratio,
        goal=goal,
        climax_seconds=climax_seconds,
        sections=sections,
        midi_parts=midi_parts,
        sound_roles=sound_roles,
    )
    report = DemoGenerationReport(
        status="success",
        output_dir=_to_repo_relative(output_dir),
        source_dataset_folders=sorted(set(item["folder"] for item in examples[:8])),
        source_example_ids=sorted(set(source_ids)),
        transformations_applied=transforms,
    )
    plan_json = output_dir / "demo_composition_plan.json"
    report_json = output_dir / "generation_report.json"
    plan_md = output_dir / "demo_composition_plan.md"
    report_md = output_dir / "generation_report.md"
    plan_json.write_text(json.dumps(asdict(plan), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    report_payload = asdict(report)
    report_payload.update(
        {
            "ratio_timing": {"ratio": ratio, "duration_seconds": duration_seconds, "climax_seconds": climax_seconds},
            "output_midi_paths": {
                "song": _to_repo_relative(song_path),
                "drums": _to_repo_relative(output_dir / "generated_drums.mid"),
                "bass": _to_repo_relative(output_dir / "generated_bass.mid"),
                "chords": _to_repo_relative(output_dir / "generated_chords.mid"),
                "lead": _to_repo_relative(output_dir / "generated_lead.mid"),
                "texture_bed": _to_repo_relative(output_dir / "generated_texture_motifs.mid"),
            },
            "note_counts": track_note_counts,
            "model_training_claim": False,
            "synplant_automation_claim": False,
        }
    )
    report_json.write_text(json.dumps(report_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    plan_md.write_text(f"# Tangible Demo Composition Plan\n\n- climax_seconds: `{climax_seconds}`\n", encoding="utf-8")
    report_md.write_text(
        "# Tangible Demo Generation Report\n\n- prototype_generated_from_existing_examples: `true`\n- not_model_trained: `true`\n- synplant_automation_claim: `false`\n",
        encoding="utf-8",
    )

    # seed suggestions (private path file ignored by gitignore)
    suggestions_path = ROOT_DIR / "datasets" / "sample_libraries" / "local_sounds_desktop" / "sample_seed_records.jsonl"
    suggestions = _read_jsonl(suggestions_path)
    if suggestions:
        chosen = suggestions[:6]
        rows = []
        for role, item in zip(["drums", "bass", "chords", "lead", "texture_bed", "transition_fx"], chosen):
            rows.append(
                asdict(
                    DemoSynplantSeedSuggestion(
                        track_role=role,  # type: ignore[arg-type]
                        requested_texture=f"{role}_texture",
                        sample_id=str(item.get("sample_id", "")),
                        source_path=str(item.get("source_path", "")),
                        asset_type_guess=str(item.get("asset_type_guess", "unknown")),
                        reason="Matched by heuristic role/asset pairing.",
                        training_allowed_assumption="user_local_claimed_for_research_only",
                        requires_human_review=bool(item.get("needs_human_review", True)),
                    )
                )
            )
        (output_dir / "synplant_seed_suggestions.json").write_text(json.dumps(rows, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        (output_dir / "synplant_seed_suggestions.md").write_text(
            "# Synplant Seed Suggestions\n\n" + "\n".join([f"- `{r['track_role']}` -> `{r['sample_id']}`" for r in rows]) + "\n",
            encoding="utf-8",
        )
    else:
        (output_dir / "synplant_seed_suggestions.md").write_text(
            "# Synplant Seed Suggestions\n\nNo local sample index found. Run `scripts\\dev.cmd index-sample-library config/sample_libraries/local_sounds_library.json`.\n",
            encoding="utf-8",
        )

    (output_dir / "ableton_track_plan.json").write_text(
        json.dumps({"tracks": [{"track_name": "drums", "midi_file": "generated_drums.mid"}]}, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "ableton_track_plan.md").write_text("# Ableton Track Plan\n\n- drums: generated_drums.mid\n", encoding="utf-8")
    print(f"CLIMAX_SECONDS={climax_seconds}")
    print("SAMPLE_INDEX_PRESENT=" + str(bool(suggestions)))
    print(f"TANGIBLE_DEMO_OUTPUT_DIR={_to_repo_relative(output_dir)}")
    print(f"TANGIBLE_DEMO_REPORT_JSON={_to_repo_relative(report_json)}")
    print(f"TANGIBLE_DEMO_REPORT_MD={_to_repo_relative(report_md)}")
    return {"output_dir": _to_repo_relative(output_dir), "note_counts": track_note_counts, "climax_seconds": climax_seconds}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a tangible MIDI demo from existing generative examples.")
    parser.add_argument("duration", nargs="?", type=float, default=180.0)
    parser.add_argument("ratio", nargs="?", default="golden_ratio")
    parser.add_argument("goal", nargs="?", default="climax")
    args = parser.parse_args()
    generate_tangible_demo(duration_seconds=args.duration, ratio=args.ratio, goal=args.goal)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
