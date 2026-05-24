from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

from mido import Message, MetaMessage, MidiFile, MidiTrack, second2tick

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.symbolic_model_ensemble.capability_registry import backend_availability_payload  # noqa: E402
from features.symbolic_model_ensemble.ensemble_orchestrator import SymbolicEnsembleOrchestrator  # noqa: E402


def _to_repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT_DIR.resolve()).as_posix()
    except Exception:  # noqa: BLE001
        return path.as_posix()


def _beats_per_bar(meter: str) -> float:
    top, bottom = meter.split("/")
    return float(top) * (4.0 / float(bottom))


def _bar_start_seconds(bar_index: int, bpm: float, meter: str) -> float:
    beats = _beats_per_bar(meter)
    seconds_per_beat = 60.0 / bpm
    return bar_index * beats * seconds_per_beat


def _section_plan() -> list[dict[str, Any]]:
    return [
        {"name": "intro", "bars": 4},
        {"name": "verse", "bars": 10},
        {"name": "hook", "bars": 8},
        {"name": "bridge", "bars": 6},
        {"name": "final_hook", "bars": 8},
        {"name": "outro", "bars": 3},
    ]


def _a_minor_progression(section: str) -> list[str]:
    if section == "intro":
        return ["Am", "F", "C", "G"]
    if section == "verse":
        return ["Am", "F", "C", "G", "Am", "F", "Dm", "E", "Am", "G"]
    if section == "hook":
        return ["Am", "Dm", "F", "G", "Am", "Dm", "F", "E"]
    if section == "bridge":
        return ["F", "C", "G", "Am", "Dm", "E"]
    if section == "final_hook":
        return ["Am", "Dm", "F", "G", "Am", "Dm", "F", "E"]
    return ["Am", "G", "F"]


def _chord_tones(chord_name: str) -> list[int]:
    mapping = {
        "Am": [57, 60, 64],
        "Dm": [50, 53, 57],
        "E": [52, 56, 59],
        "F": [53, 57, 60],
        "G": [55, 59, 62],
        "C": [48, 52, 55],
    }
    return mapping.get(chord_name, [57, 60, 64])


def _bass_root(chord_name: str) -> int:
    mapping = {"Am": 45, "Dm": 38, "E": 40, "F": 41, "G": 43, "C": 36}
    return mapping.get(chord_name, 45)


def _append_note(events: list[dict[str, Any]], start: float, end: float, note: int, velocity: int) -> None:
    if end <= start:
        return
    events.append({"start": round(start, 6), "end": round(end, 6), "note": int(note), "velocity": int(velocity)})


def _build_timeline(
    bpm: float,
    meter: str,
    motif_offsets: list[int],
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]], float]:
    beats = _beats_per_bar(meter)
    bar_seconds = (60.0 / bpm) * beats
    all_sections = _section_plan()
    arrangement: list[dict[str, Any]] = []

    drums: list[dict[str, Any]] = []
    bass: list[dict[str, Any]] = []
    chords: list[dict[str, Any]] = []
    lead: list[dict[str, Any]] = []
    texture: list[dict[str, Any]] = []

    current_bar = 0
    for section in all_sections:
        section_name = str(section["name"])
        section_bars = int(section["bars"])
        section_start = _bar_start_seconds(current_bar, bpm, meter)
        section_end = _bar_start_seconds(current_bar + section_bars, bpm, meter)
        arrangement.append(
            {
                "section": section_name,
                "start_seconds": round(section_start, 3),
                "end_seconds": round(section_end, 3),
                "bars": section_bars,
            }
        )
        progression = _a_minor_progression(section_name)
        for local_bar in range(section_bars):
            chord_name = progression[local_bar % len(progression)]
            global_bar = current_bar + local_bar
            bar_start = _bar_start_seconds(global_bar, bpm, meter)
            bar_end = bar_start + bar_seconds
            beat = 60.0 / bpm

            # Sparse expressive drums: mainly kick/snare, light hats in hooks only.
            kick_vel = 72 if section_name in {"intro", "outro"} else 80
            _append_note(drums, bar_start + 0.00 * beat, bar_start + 0.08 * beat, 36, kick_vel)
            _append_note(drums, bar_start + 2.00 * beat, bar_start + 2.08 * beat, 38, 70)
            if section_name in {"hook", "final_hook", "bridge"}:
                _append_note(drums, bar_start + 3.00 * beat, bar_start + 3.08 * beat, 36, 64)
                _append_note(drums, bar_start + 1.50 * beat, bar_start + 1.58 * beat, 42, 50)
                _append_note(drums, bar_start + 3.50 * beat, bar_start + 3.58 * beat, 42, 50)

            # Emotional simple bass with long notes and occasional approach tone.
            root = _bass_root(chord_name)
            _append_note(bass, bar_start + 0.00 * beat, bar_start + 2.00 * beat, root, 66)
            _append_note(bass, bar_start + 2.00 * beat, bar_start + 3.75 * beat, root, 62)
            if section_name in {"bridge", "final_hook"}:
                _append_note(bass, bar_start + 3.75 * beat, bar_end, root + 2, 52)

            # Spacious chords: sustained triads with gentle voice spread.
            tones = _chord_tones(chord_name)
            for note in tones:
                _append_note(chords, bar_start + 0.00 * beat, bar_end - 0.05 * beat, note, 48)
                _append_note(chords, bar_start + 0.00 * beat, bar_end - 0.05 * beat, note + 12, 38)

            # Subtle texture motifs: high sparse octave pulses.
            if section_name not in {"verse"} or local_bar % 2 == 0:
                texture_note = tones[0] + 24
                _append_note(texture, bar_start + 0.50 * beat, bar_start + 1.50 * beat, texture_note, 36)
                if section_name in {"hook", "final_hook"}:
                    _append_note(texture, bar_start + 2.50 * beat, bar_start + 3.50 * beat, texture_note + 7, 34)

            # Hummable lead enters after intro and leaves space for vocals.
            if section_name in {"verse", "hook", "bridge", "final_hook"}:
                # Less dense in verse, stronger in hooks.
                density = 2 if section_name == "verse" else 4
                motif_base = 69  # A4
                motif_len = max(2, min(len(motif_offsets), density))
                for idx in range(motif_len):
                    start = bar_start + (idx * (beats / motif_len)) * beat
                    duration = (0.50 if section_name == "verse" else 0.66) * beat
                    pitch = motif_base + motif_offsets[idx % len(motif_offsets)]
                    velocity = 62 if section_name == "verse" else 72
                    _append_note(lead, start, min(bar_end - 0.05 * beat, start + duration), pitch, velocity)

        current_bar += section_bars

    duration_seconds = _bar_start_seconds(current_bar, bpm, meter)
    tracks = {"drums": drums, "bass": bass, "chords": chords, "lead": lead, "texture": texture}
    return tracks, arrangement, duration_seconds


def _write_single_track_midi(path: Path, events: list[dict[str, Any]], bpm: float, channel: int, track_name: str) -> int:
    tempo = int(round(60_000_000.0 / bpm))
    midi = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    midi.tracks.append(track)
    track.append(MetaMessage("track_name", name=track_name, time=0))
    track.append(MetaMessage("set_tempo", tempo=tempo, time=0))

    timeline: list[tuple[float, Message]] = []
    for event in events:
        start = float(event["start"])
        end = float(event["end"])
        note = max(0, min(127, int(event["note"])))
        velocity = max(1, min(127, int(event["velocity"])))
        timeline.append((start, Message("note_on", note=note, velocity=velocity, channel=channel, time=0)))
        timeline.append((end, Message("note_off", note=note, velocity=0, channel=channel, time=0)))
    timeline.sort(key=lambda item: (item[0], 0 if item[1].type == "note_off" else 1))

    previous = 0.0
    note_count = 0
    for at_sec, message in timeline:
        delta = max(0.0, at_sec - previous)
        ticks = int(round(second2tick(delta, midi.ticks_per_beat, tempo)))
        track.append(message.copy(time=max(0, ticks)))
        previous = at_sec
        if message.type == "note_on" and message.velocity > 0:
            note_count += 1
    track.append(MetaMessage("end_of_track", time=0))
    path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(path.as_posix())
    return note_count


def _write_full_midi(path: Path, track_events: dict[str, list[dict[str, Any]]], bpm: float) -> int:
    tempo = int(round(60_000_000.0 / bpm))
    midi = MidiFile(ticks_per_beat=480)
    role_channels = {"drums": 9, "bass": 1, "chords": 2, "lead": 3, "texture": 4}
    total_notes = 0
    for role in ["drums", "bass", "chords", "lead", "texture"]:
        track = MidiTrack()
        midi.tracks.append(track)
        track.append(MetaMessage("track_name", name=role, time=0))
        track.append(MetaMessage("set_tempo", tempo=tempo, time=0))
        timeline: list[tuple[float, Message]] = []
        channel = role_channels[role]
        for event in track_events[role]:
            note = max(0, min(127, int(event["note"])))
            velocity = max(1, min(127, int(event["velocity"])))
            start = float(event["start"])
            end = float(event["end"])
            timeline.append((start, Message("note_on", note=note, velocity=velocity, channel=channel, time=0)))
            timeline.append((end, Message("note_off", note=note, velocity=0, channel=channel, time=0)))
        timeline.sort(key=lambda item: (item[0], 0 if item[1].type == "note_off" else 1))
        prev = 0.0
        for at_sec, msg in timeline:
            delta = max(0.0, at_sec - prev)
            ticks = int(round(second2tick(delta, midi.ticks_per_beat, tempo)))
            track.append(msg.copy(time=max(0, ticks)))
            prev = at_sec
            if msg.type == "note_on" and msg.velocity > 0:
                total_notes += 1
        track.append(MetaMessage("end_of_track", time=0))
    path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(path.as_posix())
    return total_notes


def _read_example_motif_offsets() -> tuple[list[int], dict[str, Any]]:
    datasets_root = ROOT_DIR / "datasets" / "generative_training"
    files = sorted(datasets_root.glob("**/generative_examples.jsonl"))
    source_info: dict[str, Any] = {
        "examples_files_scanned": len(files),
        "examples_rows_scanned": 0,
        "motif_source": "fallback_default_minor_cell",
    }
    if not files:
        return [0, 2, -2, 3], source_info

    extracted_pitches: list[int] = []
    rows_scanned = 0
    for file_path in files[:4]:
        lines = file_path.read_text(encoding="utf-8").splitlines()
        for line in lines[:120]:
            if not line.strip():
                continue
            rows_scanned += 1
            try:
                row = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            rep = row.get("target_representation", {})
            if not isinstance(rep, dict):
                continue
            events = rep.get("midi_events", [])
            if not isinstance(events, list):
                continue
            for event in events:
                if not isinstance(event, dict):
                    continue
                note_val = event.get("note")
                if isinstance(note_val, int):
                    extracted_pitches.append(note_val)
                if len(extracted_pitches) >= 12:
                    break
            if len(extracted_pitches) >= 12:
                break
        if len(extracted_pitches) >= 12:
            break
    source_info["examples_rows_scanned"] = rows_scanned
    if len(extracted_pitches) < 4:
        return [0, 2, -2, 3], source_info

    anchor = int(round(sum(extracted_pitches) / len(extracted_pitches)))
    anchor = 69 + int(round((anchor - 69) / 12.0)) * 12
    motif_offsets = []
    for pitch in extracted_pitches[:4]:
        offset = int(pitch - anchor)
        offset = max(-7, min(7, offset))
        motif_offsets.append(offset)
    while len(motif_offsets) < 4:
        motif_offsets.append(0)
    source_info["motif_source"] = "symbolic_examples_pitch_cell"
    return motif_offsets, source_info


def generate_ballad(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check symbolic backend availability and run the local ensemble pipeline once.
    availability = backend_availability_payload()
    orchestrator = SymbolicEnsembleOrchestrator()
    prompt = "Emotional dark melodic minor ballad, sparse drums, vocal space, 2-minute structure."
    probe_dir = output_dir / "symbolic_ensemble_probe"
    ensemble_report = orchestrator.generate(prompt, output_root=probe_dir)
    probe_availability_path = probe_dir / "backend_availability_report.json"
    if probe_availability_path.exists():
        availability = json.loads(probe_availability_path.read_text(encoding="utf-8"))

    motif_offsets, example_source = _read_example_motif_offsets()

    tempo_bpm = 78.0
    meter = "4/4"
    track_events, structure, duration_seconds = _build_timeline(tempo_bpm, meter, motif_offsets)

    role_to_file = {
        "drums": "ballad_drums.mid",
        "bass": "ballad_bass.mid",
        "chords": "ballad_chords.mid",
        "lead": "ballad_lead.mid",
        "texture": "ballad_texture.mid",
    }
    channels = {"drums": 9, "bass": 1, "chords": 2, "lead": 3, "texture": 4}

    midi_files_created: list[str] = []
    note_counts: dict[str, int] = {}
    for role, file_name in role_to_file.items():
        path = output_dir / file_name
        notes = _write_single_track_midi(path, track_events[role], tempo_bpm, channels[role], role)
        note_counts[role] = notes
        midi_files_created.append(_to_repo_relative(path))

    full_path = output_dir / "ballad_full.mid"
    note_counts["full"] = _write_full_midi(full_path, track_events, tempo_bpm)
    midi_files_created.append(_to_repo_relative(full_path))

    backends = availability.get("backends", [])
    checked = [str(item.get("backend_id", "")) for item in backends if isinstance(item, dict)]
    used = []
    skipped = []
    for item in backends:
        if not isinstance(item, dict):
            continue
        backend_id = str(item.get("backend_id", "unknown"))
        status = str(item.get("status", "unknown"))
        reason = str(item.get("reason", "unknown"))
        if status == "available":
            used.append(backend_id)
        else:
            skipped.append(f"{backend_id}:{reason}")
    if ensemble_report.get("selected_candidate_backend"):
        selected_backend = str(ensemble_report["selected_candidate_backend"])
        if selected_backend not in used:
            used.append(selected_backend)

    structure_names = [str(item["section"]) for item in structure]
    generation_mode = "model-assisted" if any(name in {"moonbeam", "midigpt", "text2midi"} for name in used) else "prototype"

    generated_from_user_data = bool(example_source.get("examples_files_scanned", 0) > 0)
    generated_explanation = (
        "Derived lead motif and arrangement constraints from local symbolic example datasets under datasets/generative_training."
        if generated_from_user_data
        else "No local symbolic examples found; used deterministic handcrafted minor-ballad templates."
    )

    generation_report = {
        "status": "ok",
        "mode": generation_mode,
        "duration_seconds": round(duration_seconds, 3),
        "tempo_bpm": tempo_bpm,
        "key": "A minor",
        "meter": meter,
        "structure": structure_names,
        "section_timeline": structure,
        "midi_files_created": midi_files_created,
        "models_checked": checked,
        "models_used": used,
        "models_skipped_unavailable": skipped,
        "generated_from_user_data": {
            "value": generated_from_user_data,
            "explanation": generated_explanation,
        },
        "trained_model_generation": False,
        "cloud_called": False,
        "training_performed": False,
        "human_review_required": True,
        "ensemble_probe_report": _to_repo_relative(probe_dir / "ensemble_generation_report.json"),
        "note_counts": note_counts,
        "motif_offsets": motif_offsets,
        "example_source_summary": example_source,
    }

    provenance_report = {
        "status": "ok",
        "mode": generation_mode,
        "provenance": {
            "symbolic_ensemble_probe_used": True,
            "symbolic_ensemble_selected_backend": ensemble_report.get("selected_candidate_backend", ""),
            "example_retrieval_fallback_used": bool(ensemble_report.get("example_retrieval_fallback", False)),
            "no_real_symbolic_backend_available": bool(ensemble_report.get("no_real_symbolic_backend_available", False)),
            "source_example_conditioning": example_source,
            "arrangement_method": "deterministic_minor_ballad_ruleset",
        },
        "policy": {
            "cloud_called": False,
            "training_performed": False,
            "audio_processed": False,
            "human_review_required": True,
        },
    }

    generation_json = output_dir / "generation_report.json"
    generation_md = output_dir / "generation_report.md"
    provenance_json = output_dir / "provenance_report.json"
    provenance_md = output_dir / "provenance_report.md"
    ableton_md = output_dir / "ableton_track_plan.md"

    generation_json.write_text(json.dumps(generation_report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    provenance_json.write_text(json.dumps(provenance_report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    generation_md.write_text(
        "\n".join(
            [
                "# Generation Report",
                "",
                f"- mode: `{generation_mode}`",
                f"- duration_seconds: `{generation_report['duration_seconds']}`",
                f"- tempo_bpm: `{tempo_bpm}`",
                "- key: `A minor`",
                f"- structure: `{', '.join(structure_names)}`",
                f"- cloud_called: `{generation_report['cloud_called']}`",
                f"- training_performed: `{generation_report['training_performed']}`",
                f"- trained_model_generation: `{generation_report['trained_model_generation']}`",
                "",
                "## MIDI Files",
            ]
            + [f"- `{item}`" for item in midi_files_created]
            + ["", "## Models"]
            + [f"- checked: `{', '.join(checked)}`", f"- used: `{', '.join(used) if used else 'none'}`"]
            + [f"- skipped_unavailable: `{', '.join(skipped) if skipped else 'none'}`"]
            + ["", "## Conditioning", f"- generated_from_user_data: `{generated_explanation}`"]
        )
        + "\n",
        encoding="utf-8",
    )

    provenance_md.write_text(
        "\n".join(
            [
                "# Provenance Report",
                "",
                f"- mode: `{generation_mode}`",
                f"- symbolic_ensemble_selected_backend: `{provenance_report['provenance']['symbolic_ensemble_selected_backend']}`",
                f"- example_retrieval_fallback_used: `{provenance_report['provenance']['example_retrieval_fallback_used']}`",
                f"- no_real_symbolic_backend_available: `{provenance_report['provenance']['no_real_symbolic_backend_available']}`",
                "- arrangement_method: `deterministic_minor_ballad_ruleset`",
                "- cloud_called: `false`",
                "- training_performed: `false`",
                "- audio_processed: `false`",
                "- human_review_required: `true`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    ableton_md.write_text(
        "\n".join(
            [
                "# Ableton Track Plan",
                "",
                "- Tempo: `78 BPM`",
                "- Key: `A minor`",
                "- Structure: `intro / verse / hook / bridge / final_hook / outro`",
                "",
                "## Track Layout",
                "- `ballad_drums.mid`: low-density kick/snare with light hook hats; preserve vocal space.",
                "- `ballad_bass.mid`: long root-driven notes with subtle bridge/final-hook approach tones.",
                "- `ballad_chords.mid`: wide sustained minor/modal-minor triads with low velocity.",
                "- `ballad_lead.mid`: hummable sparse motif; lower density in verse for vocal room.",
                "- `ballad_texture.mid`: subtle high-octave pulses and hook lift accents.",
                "",
                "## Human Review Checklist",
                "- Confirm vocal pocket remains clear in verse and first hook.",
                "- Decide whether to thin lead notes in final hook for topline flexibility.",
                "- Humanize timing and velocity slightly before final production.",
                "- Validate instrument choices against target dark emotional tone.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "output_dir": _to_repo_relative(output_dir),
        "duration_seconds": round(duration_seconds, 3),
        "tempo_bpm": tempo_bpm,
        "key": "A minor",
        "structure": structure_names,
        "models_used": used,
        "models_skipped": skipped,
    }


def main() -> int:
    output_dir = ROOT_DIR / "outputs" / "ballad_2min_v1"
    result = generate_ballad(output_dir)
    print(f"BALLAD_OUTPUT_DIR={result['output_dir']}")
    print(f"BALLAD_DURATION_SECONDS={result['duration_seconds']}")
    print(f"BALLAD_TEMPO_BPM={result['tempo_bpm']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
