from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any

from mido import Message, MetaMessage, MidiFile, MidiTrack, bpm2tempo


def _safe_rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _seed_int(source: str) -> int:
    return int(hashlib.sha256(source.encode("utf-8")).hexdigest()[:8], 16)


def _note_pattern(seed: int, bars: int, base_pitch: int, complexity: int) -> list[tuple[float, float, int, int]]:
    beats_total = max(4, bars * 4)
    out: list[tuple[float, float, int, int]] = []
    step = max(1, 4 - complexity)
    for beat in range(0, beats_total, step):
        if ((beat + seed) % (3 + complexity)) == 0:
            continue
        pitch = base_pitch + (((beat + seed) % (6 + complexity)) - 2)
        velocity = 70 + ((seed + beat * 7) % 36)
        start = float(beat)
        duration = 0.45 if complexity >= 2 else 0.8
        out.append((start, min(float(beats_total), start + duration), pitch, min(120, velocity)))
    if not out:
        out.append((0.0, 0.75, base_pitch, 92))
    return out


def write_buddy_midi(
    output_path: Path,
    *,
    bpm: float,
    notes: list[tuple[float, float, int, int]],
    channel: int,
    program: int = 0,
) -> None:
    midi = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    midi.tracks.append(track)
    tempo = int(bpm2tempo(max(40.0, min(220.0, bpm))))
    track.append(MetaMessage("set_tempo", tempo=tempo, time=0))
    if channel != 9:
        track.append(Message("program_change", program=program % 128, channel=channel, time=0))

    events: list[tuple[float, Message]] = []
    for start_beat, end_beat, pitch, velocity in notes:
        start_tick = int(max(0.0, start_beat) * midi.ticks_per_beat)
        end_tick = int(max(start_beat + 0.1, end_beat) * midi.ticks_per_beat)
        events.append((float(start_tick), Message("note_on", note=max(24, min(96, pitch)), velocity=velocity, channel=channel)))
        events.append((float(end_tick), Message("note_off", note=max(24, min(96, pitch)), velocity=0, channel=channel)))
    events.sort(key=lambda item: item[0])
    last_tick = 0
    for abs_tick, msg in events:
        tick = int(abs_tick)
        delta = max(0, tick - last_tick)
        msg.time = delta
        track.append(msg)
        last_tick = tick
    track.append(MetaMessage("end_of_track", time=0))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(str(output_path))


def generate_buddy_pack_for_clip(
    clip_row: dict[str, Any],
    *,
    clip_index: int,
    project_root: Path,
    output_root: Path,
) -> dict[str, Any]:
    clip_id = str(clip_row.get("candidate_id", f"clip_{clip_index:02d}"))
    bpm = float(clip_row.get("tempo_bpm_estimate") or 92.0)
    bars = int(clip_row.get("bars_target") or 4)
    role = str(clip_row.get("clip_role", "loop_like"))
    seed_base = _seed_int(clip_id)

    clip_dir = output_root / "selected_clips" / f"clip_{clip_index:02d}_{clip_id}"
    overlay_dir = clip_dir / "overlay"
    response_dir = clip_dir / "response"
    section_dir = clip_dir / "section_derivations"
    mutation_dir = clip_dir / "mutations"

    overlay_specs = [
        ("bass", 40, 1, 0),
        ("chords", 52, 1, 48),
        ("drums", 36, 2, 0),
        ("lead", 67, 2, 80),
        ("texture", 60, 1, 88),
    ]
    overlay_paths: dict[str, str] = {}
    for idx, (name, base_pitch, complexity, program) in enumerate(overlay_specs):
        midi_path = overlay_dir / f"{name}_buddy.mid"
        channel = 9 if name == "drums" else (idx % 8)
        notes = _note_pattern(seed_base + idx, bars, base_pitch, complexity)
        write_buddy_midi(midi_path, bpm=bpm, notes=notes, channel=channel, program=program)
        overlay_paths[name] = _safe_rel(midi_path, project_root)

    response_path = response_dir / "call_response_buddy.mid"
    response_notes = _note_pattern(seed_base + 17, bars, 62, 2)
    for idx, note in enumerate(response_notes):
        response_notes[idx] = (note[0] + 0.5, note[1] + 0.5, note[2], note[3])
    write_buddy_midi(response_path, bpm=bpm, notes=response_notes, channel=2, program=81)

    section_paths: dict[str, str] = {}
    section_specs = [("intro", 3, 55), ("main", 4, 60), ("outro", 2, 58)]
    for idx, (name, section_bars, base_pitch) in enumerate(section_specs):
        path = section_dir / f"{name}_derivation.mid"
        notes = _note_pattern(seed_base + 31 + idx, section_bars, base_pitch, 1)
        write_buddy_midi(path, bpm=bpm, notes=notes, channel=3, program=idx * 8)
        section_paths[name] = _safe_rel(path, project_root)

    mutation_paths: dict[str, str] = {}
    mutation_specs = [
        ("groove_shift", bars, 48, 2),
        ("harmony_regravity", bars, 57, 1),
        ("texture_thicken", bars, 64, 2),
        ("energy_lift", bars, 69, 3),
    ]
    for idx, (name, mut_bars, base_pitch, complexity) in enumerate(mutation_specs):
        path = mutation_dir / f"{name}.mid"
        notes = _note_pattern(seed_base + 71 + idx, mut_bars, base_pitch, complexity)
        write_buddy_midi(path, bpm=min(180.0, bpm + idx * 2), notes=notes, channel=4 + (idx % 3), program=40 + idx * 5)
        mutation_paths[name] = _safe_rel(path, project_root)

    manifest = {
        "clip_index": clip_index,
        "clip_id": clip_id,
        "source_id": str(clip_row.get("source_id", "")),
        "clip_role": role,
        "bars_target": bars,
        "tempo_bpm_estimate": bpm,
        "transformation_policy": {
            "direct_melody_copy": False,
            "target": "preserve_relational_feel_not_literal_phrase",
            "notes": [
                "Buddy MIDI is generated from deterministic abstractions only.",
                "No source MIDI extraction or source melody transfer is used.",
            ],
        },
        "overlay_buddies": overlay_paths,
        "response_buddy": _safe_rel(response_path, project_root),
        "section_derivations": section_paths,
        "mutation_buddies": mutation_paths,
    }
    manifest_path = clip_dir / "buddy_pack_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return {
        "clip_manifest_path": _safe_rel(manifest_path, project_root),
        "clip_dir": _safe_rel(clip_dir, project_root),
        "overlay_count": len(overlay_paths),
        "response_count": 1,
        "section_count": len(section_paths),
        "mutation_count": len(mutation_paths),
    }


def generate_buddy_pack_for_extracted_loop(
    loop_row: dict[str, Any],
    *,
    clip_index: int,
    project_root: Path,
    output_root: Path,
) -> dict[str, Any]:
    clip_id = str(loop_row.get("clip_id", f"clip_{clip_index:02d}"))
    bpm = float(loop_row.get("tempo_bpm_estimate") or 92.0)
    bars = int(loop_row.get("bars_target") or 4)
    role = str(loop_row.get("texture_role_hint", "loop_like"))
    seed_base = _seed_int(clip_id)

    clip_dir = output_root / f"clip_{clip_index:03d}_{clip_id}"
    overlay_dir = clip_dir / "overlay"
    continuation_dir = clip_dir / "continuation"
    section_dir = clip_dir / "section_derivation"
    mutation_dir = clip_dir / "mutation"

    overlay_specs = [
        ("overlay_drums", 36, 2, 0),
        ("overlay_bass", 41, 2, 32),
        ("overlay_chords", 53, 1, 48),
        ("overlay_texture", 62, 1, 88),
    ]
    overlay_paths: dict[str, str] = {}
    for idx, (name, base_pitch, complexity, program) in enumerate(overlay_specs):
        midi_path = overlay_dir / f"{name}.mid"
        channel = 9 if "drums" in name else (idx % 8)
        notes = _note_pattern(seed_base + idx, bars, base_pitch, complexity)
        write_buddy_midi(midi_path, bpm=bpm, notes=notes, channel=channel, program=program)
        overlay_paths[name] = _safe_rel(midi_path, project_root)

    continuation_path = continuation_dir / "continuation_buddy.mid"
    continuation_notes = _note_pattern(seed_base + 37, bars, 60, 2)
    for idx, (start, end, pitch, velocity) in enumerate(continuation_notes):
        continuation_notes[idx] = (start + 0.75, end + 0.75, pitch, velocity)
    write_buddy_midi(continuation_path, bpm=bpm, notes=continuation_notes, channel=2, program=81)

    section_specs = [("section_intro", 2, 54), ("section_main", bars, 59), ("section_outro", 2, 57)]
    section_paths: dict[str, str] = {}
    for idx, (name, section_bars, base_pitch) in enumerate(section_specs):
        section_path = section_dir / f"{name}.mid"
        section_notes = _note_pattern(seed_base + 73 + idx, section_bars, base_pitch, 1)
        write_buddy_midi(section_path, bpm=bpm, notes=section_notes, channel=3, program=idx * 8)
        section_paths[name] = _safe_rel(section_path, project_root)

    mutation_specs = [("mutation_groove", 48, 2), ("mutation_harmony", 57, 1), ("mutation_energy", 67, 3)]
    mutation_paths: dict[str, str] = {}
    for idx, (name, base_pitch, complexity) in enumerate(mutation_specs):
        path = mutation_dir / f"{name}.mid"
        notes = _note_pattern(seed_base + 101 + idx, bars, base_pitch, complexity)
        write_buddy_midi(path, bpm=min(180.0, bpm + idx), notes=notes, channel=4 + idx, program=40 + idx * 5)
        mutation_paths[name] = _safe_rel(path, project_root)

    manifest = {
        "clip_id": clip_id,
        "clip_index": clip_index,
        "clip_role_hint": role,
        "source_redacted_path": str(loop_row.get("source_redacted_path", "<PRIVATE_LOCAL_PATH>/unknown")),
        "tempo_bpm_estimate": bpm,
        "bars_target": bars,
        "overlay_buddies": overlay_paths,
        "continuation_buddy": _safe_rel(continuation_path, project_root),
        "section_derivation_buddies": section_paths,
        "mutation_buddies": mutation_paths,
        "alignment_notes": [
            "MIDI buddies align to extracted source loop duration/bars.",
            "Generation remains transform-based and role-separated.",
        ],
    }
    manifest_path = clip_dir / "buddy_pack_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return {
        "clip_id": clip_id,
        "clip_manifest_path": _safe_rel(manifest_path, project_root),
        "clip_dir": _safe_rel(clip_dir, project_root),
        "best_overlay_path": overlay_paths.get("overlay_drums") or next(iter(overlay_paths.values())),
        "continuation_path": _safe_rel(continuation_path, project_root),
        "best_section_path": section_paths.get("section_main") or next(iter(section_paths.values())),
    }
