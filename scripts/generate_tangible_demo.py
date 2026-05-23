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

SUPPORTED_TASKS = {
    "continuation",
    "phrase_continuation",
    "groove_continuation",
    "harmony_continuation",
    "call_response",
    "section_transition",
    "buildup_to_release",
}
PHI = (1.0 + math.sqrt(5.0)) / 2.0


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


def _clamp_note(note: int) -> int:
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


def _discover_dataset_folders(root: Path) -> list[Path]:
    folders = sorted(path.parent for path in root.glob("**/generative_examples.jsonl"))

    def _priority(folder: Path) -> tuple[int, str]:
        text = folder.as_posix().lower()
        if "ghost" in text:
            return (0, text)
        if "sunday" in text:
            return (1, text)
        return (2, text)

    return sorted(folders, key=_priority)


def _extract_events(row: dict[str, Any]) -> list[dict[str, float]]:
    rep = row.get("target_representation")
    if not isinstance(rep, dict):
        return []
    raw = rep.get("midi_events")
    if not isinstance(raw, list):
        return []
    events: list[dict[str, float]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        start = _safe_float(item.get("start"), -1.0)
        end = _safe_float(item.get("end"), -1.0)
        note = _safe_int(item.get("note"), -1)
        vel = _safe_int(item.get("velocity"), 64)
        if start < 0 or end <= start or note < 0:
            continue
        events.append(
            {
                "start": round(start, 6),
                "end": round(end, 6),
                "note": float(_clamp_note(note)),
                "velocity": float(max(1, min(127, vel))),
            }
        )
    return sorted(events, key=lambda e: e["start"])


def _normalize_start(events: list[dict[str, float]]) -> list[dict[str, float]]:
    if not events:
        return []
    offset = min(item["start"] for item in events)
    out: list[dict[str, float]] = []
    for item in events:
        out.append(
            {
                "start": round(max(0.0, item["start"] - offset), 6),
                "end": round(max(0.0, item["end"] - offset), 6),
                "note": item["note"],
                "velocity": item["velocity"],
            }
        )
    return out


def _transform_events(events: list[dict[str, float]], semitones: int, stride: int, velocity_scale: float) -> list[dict[str, float]]:
    stride = max(1, stride)
    transformed: list[dict[str, float]] = []
    for idx, item in enumerate(events):
        if idx % stride != 0:
            continue
        transformed.append(
            {
                "start": item["start"],
                "end": item["end"],
                "note": float(_clamp_note(int(round(item["note"])) + semitones)),
                "velocity": float(max(1, min(127, int(round(item["velocity"] * velocity_scale))))),
            }
        )
    return transformed


def _event_span(events: list[dict[str, float]]) -> float:
    if not events:
        return 0.0
    return max(0.0, max(item["end"] for item in events) - min(item["start"] for item in events))


def _assign_channel(role: str) -> int:
    channels = {"drums": 9, "bass": 1, "chords": 2, "lead": 3, "counter_melody": 4, "texture_bed": 5, "transition_fx": 6}
    return channels.get(role, 0)


def _task_preferences_for_role(role: str) -> list[str]:
    mapping = {
        "drums": ["groove_continuation", "call_response", "section_transition"],
        "bass": ["continuation", "harmony_continuation"],
        "chords": ["harmony_continuation", "phrase_continuation"],
        "lead": ["phrase_continuation", "call_response"],
        "counter_melody": ["call_response", "continuation"],
        "texture_bed": ["section_transition", "buildup_to_release"],
        "transition_fx": ["section_transition", "buildup_to_release"],
    }
    return mapping.get(role, ["continuation"])


def _build_sections(duration_seconds: float, ratio: str, goal: str) -> tuple[list[DemoSection], float]:
    climax_seconds = round(duration_seconds / PHI, 3) if ratio == "golden_ratio" else round(duration_seconds * 0.62, 3)
    intro_end = round(max(8.0, duration_seconds * 0.14), 3)
    build_end = round(max(intro_end + 8.0, climax_seconds - duration_seconds * 0.12), 3)
    climax_end = round(min(duration_seconds * 0.82, climax_seconds + duration_seconds * 0.06), 3)
    release_end = round(min(duration_seconds * 0.92, climax_end + duration_seconds * 0.16), 3)
    sections = [
        DemoSection("intro", "intro", 0.0, intro_end, "establish material"),
        DemoSection("build", "build", intro_end, build_end, "increase tension"),
        DemoSection("climax", "climax", build_end, climax_end, goal),
        DemoSection("release", "release", climax_end, release_end, "inverse_phi_decay"),
        DemoSection("outro", "outro", release_end, round(duration_seconds, 3), "resolve"),
    ]
    return sections, climax_seconds


def _write_track_midi(path: Path, events: list[dict[str, float]], channel: int, tempo_bpm: float = 120.0) -> int:
    midi = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    midi.tracks.append(track)
    tempo = int(round(60_000_000.0 / max(1.0, tempo_bpm)))
    track.append(MetaMessage("set_tempo", tempo=tempo, time=0))
    timeline: list[tuple[float, Message]] = []
    for event in events:
        start = _safe_float(event["start"], 0.0)
        end = max(start + 1e-4, _safe_float(event["end"], start + 1e-4))
        note = _clamp_note(_safe_int(event["note"], 60))
        velocity = max(1, min(127, _safe_int(event["velocity"], 64)))
        timeline.append((start, Message("note_on", channel=channel, note=note, velocity=velocity, time=0)))
        timeline.append((end, Message("note_off", channel=channel, note=note, velocity=0, time=0)))
    timeline.sort(key=lambda x: (x[0], 0 if x[1].type == "note_off" else 1))
    prev = 0.0
    notes = 0
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


def _choose_seed_suggestions(sample_records_path: Path, role_requests: dict[str, str]) -> tuple[list[dict[str, Any]], bool]:
    if not sample_records_path.exists():
        return [], False
    records = _read_jsonl(sample_records_path)
    if not records:
        return [], True
    allowed_types = {
        "drums": {"drum_break", "drum_loop", "drum_one_shot"},
        "bass": {"bass_one_shot", "synth_one_shot"},
        "chords": {"chord_stab", "synth_one_shot", "texture"},
        "lead": {"synth_one_shot", "vocal_chop"},
        "counter_melody": {"synth_one_shot", "vocal_chop"},
        "texture_bed": {"texture", "drone", "field_recording"},
        "transition_fx": {"fx", "riser"},
    }
    suggestions: list[dict[str, Any]] = []
    for role, texture in role_requests.items():
        match = next(
            (
                row
                for row in records
                if isinstance(row, dict) and str(row.get("asset_type_guess", "unknown")) in allowed_types.get(role, {"unknown"})
            ),
            None,
        )
        if match is None:
            continue
        suggestions.append(
            asdict(
                DemoSynplantSeedSuggestion(
                    track_role=role,  # type: ignore[arg-type]
                    requested_texture=texture,
                    sample_id=str(match.get("sample_id", "")),
                    source_path=str(match.get("source_path", "")),
                    asset_type_guess=str(match.get("asset_type_guess", "unknown")),
                    reason=f"Matched heuristic asset type for {role}",
                    training_allowed_assumption="user_local_claimed_for_research_only",
                    requires_human_review=bool(match.get("needs_human_review", True)),
                )
            )
        )
    return suggestions, True


def calculate_climax_seconds(duration_seconds: float, ratio: str) -> float:
    return round(duration_seconds / PHI, 3) if ratio == "golden_ratio" else round(duration_seconds * 0.62, 3)


def _to_repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT_DIR.resolve()).as_posix()
    except Exception:  # noqa: BLE001
        return path.as_posix()


def generate_tangible_demo(
    duration_seconds: float = 180.0,
    ratio: str = "golden_ratio",
    goal: str = "climax",
    datasets_root: Path | None = None,
    output_root: Path | None = None,
    sample_records_path: Path | None = None,
) -> dict[str, Any]:
    datasets_root = datasets_root or (ROOT_DIR / "datasets" / "generative_training")
    output_root = output_root or (ROOT_DIR / "outputs" / "tangible_generation_v1")
    sample_records_path = sample_records_path or (
        ROOT_DIR / "datasets" / "sample_libraries" / "local_sounds_desktop" / "sample_seed_records.jsonl"
    )
    output_root.mkdir(parents=True, exist_ok=True)
    dataset_folders = _discover_dataset_folders(datasets_root)
    if not dataset_folders:
        raise FileNotFoundError(f"No generative datasets found under {datasets_root.as_posix()}")
    role_requests = {
        "drums": "groove-driving rhythmic backbone",
        "bass": "low-end pulse",
        "chords": "harmonic support layer",
        "lead": "foreground melodic hook",
        "counter_melody": "call/response melodic layer",
        "texture_bed": "ambient sustained texture",
        "transition_fx": "section transitions and swells",
    }
    sections, climax_seconds = _build_sections(duration_seconds, ratio, goal)

    pool: list[dict[str, Any]] = []
    source_dataset_paths: list[str] = []
    for folder in dataset_folders:
        rows = _read_jsonl(folder / "generative_examples.jsonl")
        if not rows:
            continue
        source_dataset_paths.append(_to_repo_relative(folder))
        for row in rows:
            task = str(row.get("task_type", "")).strip().lower()
            split = str(row.get("split_recommendation", "")).strip().lower()
            quality = _safe_float(row.get("quality_score", {}).get("final_score"), 0.0)
            if task not in SUPPORTED_TASKS or split not in {"train", "validation"} or quality < 0.45:
                continue
            events = _extract_events(row)
            if not events:
                continue
            pool.append(
                {
                    "task": task,
                    "quality": quality,
                    "example_id": str(row.get("example_id", "")),
                    "events": events,
                }
            )
    if not pool:
        raise RuntimeError("No usable generative examples found for tangible demo.")
    pool.sort(key=lambda row: (-row["quality"], row["example_id"]))

    track_events: dict[str, list[dict[str, float]]] = {role: [] for role in role_requests}
    midi_parts: list[DemoMidiPart] = []
    sound_roles: list[DemoSoundRole] = []
    all_source_ids: list[str] = []
    all_transformations: list[str] = []

    for role_index, (role, texture) in enumerate(role_requests.items()):
        prefs = _task_preferences_for_role(role)
        candidates = [row for row in pool if row["task"] in prefs][:6]
        if not candidates:
            candidates = pool[:6]
        role_part_events: list[dict[str, float]] = []
        part_source_ids: list[str] = []
        transforms: list[str] = []
        for section_index, section in enumerate(sections):
            source = candidates[(role_index + section_index) % len(candidates)]
            base = _normalize_start(source["events"])
            semitones = ((role_index + section_index) % 5) - 2
            stride = 1 + ((role_index + section_index) % 2)
            velocity_scale = 0.85 + (((role_index * 3) + section_index) % 3) * 0.1
            transformed = _transform_events(base, semitones=semitones, stride=stride, velocity_scale=velocity_scale)
            source_span = max(0.25, _event_span(transformed))
            target_span = max(1.0, section.end_seconds - section.start_seconds)
            time_scale = max(0.4, min(1.4, target_span / source_span))
            for event in transformed:
                start = section.start_seconds + event["start"] * time_scale
                end = min(section.end_seconds, section.start_seconds + event["end"] * time_scale)
                if start >= section.end_seconds:
                    continue
                if end <= start:
                    end = min(section.end_seconds, start + 0.08)
                role_part_events.append(
                    {
                        "start": round(start, 6),
                        "end": round(end, 6),
                        "note": event["note"],
                        "velocity": event["velocity"],
                    }
                )
            part_source_ids.append(source["example_id"])
            transforms.append(
                f"{section.section_id}:transpose({semitones}),stride({stride}),velocity_scale({velocity_scale:.2f}),time_scale({time_scale:.2f})"
            )
        role_part_events.sort(key=lambda item: item["start"])
        track_events[role] = role_part_events
        midi_parts.append(
            DemoMidiPart(
                part_id=f"{role}_part",
                track_role=role,  # type: ignore[arg-type]
                source_example_ids=sorted(set(part_source_ids)),
                transformations_applied=transforms,
                note_count=len(role_part_events),
            )
        )
        sound_roles.append(
            DemoSoundRole(
                track_role=role,  # type: ignore[arg-type]
                requested_texture=texture,
                generation_method="recombined_example",
            )
        )
        all_source_ids.extend(part_source_ids)
        all_transformations.extend(transforms)

    output_midi_paths: dict[str, str] = {}
    note_counts: dict[str, int] = {}
    per_track_files = {
        "drums": "generated_drums.mid",
        "bass": "generated_bass.mid",
        "chords": "generated_chords.mid",
        "lead": "generated_lead.mid",
        "texture_bed": "generated_texture_motifs.mid",
    }
    for role, file_name in per_track_files.items():
        midi_path = output_root / file_name
        note_counts[role] = _write_track_midi(midi_path, track_events[role], channel=_assign_channel(role))
        output_midi_paths[role] = _to_repo_relative(midi_path)

    song_path = output_root / "generated_song.mid"
    song_midi = MidiFile(ticks_per_beat=480)
    tempo = int(round(60_000_000.0 / 120.0))
    song_note_count = 0
    for role, events in track_events.items():
        track = MidiTrack()
        song_midi.tracks.append(track)
        track.append(MetaMessage("track_name", name=role, time=0))
        track.append(MetaMessage("set_tempo", tempo=tempo, time=0))
        timeline: list[tuple[float, Message]] = []
        for event in events:
            note = _clamp_note(_safe_int(event["note"], 60))
            velocity = max(1, min(127, _safe_int(event["velocity"], 64)))
            start = _safe_float(event["start"], 0.0)
            end = max(start + 1e-4, _safe_float(event["end"], start + 1e-4))
            channel = _assign_channel(role)
            timeline.append((start, Message("note_on", channel=channel, note=note, velocity=velocity, time=0)))
            timeline.append((end, Message("note_off", channel=channel, note=note, velocity=0, time=0)))
        timeline.sort(key=lambda pair: (pair[0], 0 if pair[1].type == "note_off" else 1))
        prev = 0.0
        for when, msg in timeline:
            dt = int(round(second2tick(max(0.0, when - prev), song_midi.ticks_per_beat, tempo)))
            track.append(msg.copy(time=max(0, dt)))
            prev = when
            if msg.type == "note_on" and msg.velocity > 0:
                song_note_count += 1
        track.append(MetaMessage("end_of_track", time=0))
    song_midi.save(str(song_path))
    output_midi_paths["song"] = _to_repo_relative(song_path)
    note_counts["song"] = song_note_count

    composition_plan = DemoCompositionPlan(
        plan_id="tangible_generation_v1_plan",
        duration_seconds=duration_seconds,
        structure_ratio=ratio,
        goal=goal,
        climax_seconds=climax_seconds,
        sections=sections,
        midi_parts=midi_parts,
        sound_roles=sound_roles,
    )
    generation_report = DemoGenerationReport(
        status="success",
        output_dir=_to_repo_relative(output_root),
        source_dataset_folders=source_dataset_paths,
        source_example_ids=sorted(set(all_source_ids)),
        transformations_applied=all_transformations,
    )

    composition_plan_json = output_root / "demo_composition_plan.json"
    composition_plan_md = output_root / "demo_composition_plan.md"
    generation_report_json = output_root / "generation_report.json"
    generation_report_md = output_root / "generation_report.md"
    composition_plan_json.write_text(json.dumps(asdict(composition_plan), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    generation_report_json.write_text(
        json.dumps(
            {
                **asdict(generation_report),
                "ratio_timing": {"ratio": ratio, "duration_seconds": duration_seconds, "climax_seconds": climax_seconds},
                "output_midi_paths": output_midi_paths,
                "note_counts": note_counts,
                "task_types_used": sorted(set(item["task"] for item in pool)),
                "model_training_claim": False,
                "synplant_automation_claim": False,
            },
            indent=2,
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )
    composition_plan_md.write_text(
        "\n".join(
            [
                "# Tangible Demo Composition Plan",
                "",
                f"- duration_seconds: `{duration_seconds}`",
                f"- structure_ratio: `{ratio}`",
                f"- climax_seconds: `{climax_seconds}`",
                "",
                "## Sections",
            ]
            + [f"- `{section.section_id}` {section.start_seconds:.3f}s -> {section.end_seconds:.3f}s ({section.section_goal})" for section in sections]
            + ["", "## MIDI Parts"]
            + [f"- `{part.track_role}` notes={part.note_count} sources={', '.join(part.source_example_ids[:4])}" for part in midi_parts]
        )
        + "\n",
        encoding="utf-8",
    )
    generation_report_md.write_text(
        "\n".join(
            [
                "# Tangible Demo Generation Report",
                "",
                "- prototype_generated_from_existing_examples: `true`",
                "- not_model_trained: `true`",
                "- not_ground_truth: `true`",
                "- not_final_mix: `true`",
                "- needs_human_review: `true`",
                "- synplant_automation_claim: `false`",
                "",
                "## MIDI Outputs",
            ]
            + [f"- `{role}` -> `{path}` notes={note_counts.get(role, 0)}" for role, path in output_midi_paths.items()]
        )
        + "\n",
        encoding="utf-8",
    )

    seed_suggestions, sample_index_present = _choose_seed_suggestions(sample_records_path, role_requests)
    seed_json = output_root / "synplant_seed_suggestions.json"
    seed_md = output_root / "synplant_seed_suggestions.md"
    if sample_index_present and seed_suggestions:
        seed_json.write_text(json.dumps(seed_suggestions, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        seed_md.write_text(
            "\n".join(
                ["# Synplant Seed Suggestions", ""]
                + [
                    f"- `{item['track_role']}` -> `{item['asset_type_guess']}` sample `{item['sample_id']}` path `{item['source_path']}`"
                    for item in seed_suggestions
                ]
            )
            + "\n",
            encoding="utf-8",
        )
    else:
        seed_md.write_text(
            "# Synplant Seed Suggestions\n\nNo local sample index found. Run `scripts\\dev.cmd index-sample-library config/sample_libraries/local_sounds_library.json`.\n",
            encoding="utf-8",
        )

    ableton_plan = {
        "tracks": [
            {"track_name": "drums", "midi_file": "generated_drums.mid", "seed_role_hint": "drum_break_or_loop", "future_pd_or_max_role": "rhythm_macro_placeholder"},
            {"track_name": "bass", "midi_file": "generated_bass.mid", "seed_role_hint": "bass_or_synth_seed", "future_pd_or_max_role": "sub_harmonic_control_placeholder"},
            {"track_name": "chords", "midi_file": "generated_chords.mid", "seed_role_hint": "chord_stab_or_pad_seed", "future_pd_or_max_role": "harmonic_texture_placeholder"},
            {"track_name": "lead", "midi_file": "generated_lead.mid", "seed_role_hint": "vocal_or_synth_seed", "future_pd_or_max_role": "melodic_fx_macro_placeholder"},
            {"track_name": "texture", "midi_file": "generated_texture_motifs.mid", "seed_role_hint": "texture_or_drone_seed", "future_pd_or_max_role": "granular_or_drone_placeholder"},
        ],
        "human_review_checklist": [
            "Confirm role fit of MIDI material per section.",
            "Choose sample seeds manually before Synplant usage.",
            "Confirm transitions around climax and release timing.",
            "Mark successful seeds for future training records.",
        ],
    }
    (output_root / "ableton_track_plan.json").write_text(json.dumps(ableton_plan, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    (output_root / "ableton_track_plan.md").write_text(
        "\n".join(
            ["# Ableton / Max Track Plan", ""]
            + [f"- `{item['track_name']}`: `{item['midi_file']}` + `{item['seed_role_hint']}`" for item in ableton_plan["tracks"]]
            + ["", "## Human review checklist"]
            + [f"- {item}" for item in ableton_plan["human_review_checklist"]]
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"CLIMAX_SECONDS={climax_seconds}")
    print(f"SAMPLE_INDEX_PRESENT={sample_index_present}")
    if not sample_index_present:
        print("SAMPLE_INDEX_INSTRUCTION=scripts\\dev.cmd index-sample-library config/sample_libraries/local_sounds_library.json")

    return {
        "output_dir": _to_repo_relative(output_root),
        "generation_report_json": _to_repo_relative(generation_report_json),
        "generation_report_md": _to_repo_relative(generation_report_md),
        "composition_plan_json": _to_repo_relative(composition_plan_json),
        "composition_plan_md": _to_repo_relative(composition_plan_md),
        "synplant_seed_suggestions_json": _to_repo_relative(seed_json) if seed_json.exists() else "",
        "synplant_seed_suggestions_md": _to_repo_relative(seed_md),
        "ableton_track_plan_json": _to_repo_relative(output_root / "ableton_track_plan.json"),
        "ableton_track_plan_md": _to_repo_relative(output_root / "ableton_track_plan.md"),
        "note_counts": note_counts,
        "climax_seconds": climax_seconds,
        "sample_suggestions_generated": bool(seed_suggestions),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a tangible MIDI demo from existing generative examples.")
    parser.add_argument("duration", nargs="?", type=float, default=180.0, help="Target song duration in seconds")
    parser.add_argument("ratio", nargs="?", default="golden_ratio", help="Structure ratio (default: golden_ratio)")
    parser.add_argument("goal", nargs="?", default="climax", help="High-level structural goal")
    args = parser.parse_args()
    result = generate_tangible_demo(duration_seconds=args.duration, ratio=args.ratio, goal=args.goal)
    print(f"TANGIBLE_DEMO_OUTPUT_DIR={result['output_dir']}")
    print(f"TANGIBLE_DEMO_REPORT_JSON={result['generation_report_json']}")
    print(f"TANGIBLE_DEMO_REPORT_MD={result['generation_report_md']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
