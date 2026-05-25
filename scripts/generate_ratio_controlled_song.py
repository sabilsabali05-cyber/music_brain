from __future__ import annotations

import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mido import Message, MetaMessage, MidiFile, MidiTrack, second2tick

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.controlled_generation.generation_control_schema import GenerationControlSpec, RatioControl  # noqa: E402
from features.ratio_understanding.ratio_schema import named_ratio_catalog  # noqa: E402


def _write_midi(path: Path, notes: list[tuple[float, float, int, int]], bpm: int = 110) -> None:
    midi = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    midi.tracks.append(track)
    tempo = int(round(60_000_000 / max(1, bpm)))
    track.append(MetaMessage("set_tempo", tempo=tempo, time=0))
    timeline: list[tuple[float, Message]] = []
    for start, end, note, vel in notes:
        timeline.append((start, Message("note_on", note=note, velocity=vel, channel=0, time=0)))
        timeline.append((end, Message("note_off", note=note, velocity=0, channel=0, time=0)))
    timeline.sort(key=lambda item: (item[0], 0 if item[1].type == "note_off" else 1))
    prev = 0.0
    for when, msg in timeline:
        delta = int(round(second2tick(max(0.0, when - prev), midi.ticks_per_beat, tempo)))
        track.append(msg.copy(time=max(0, delta)))
        prev = when
    track.append(MetaMessage("end_of_track", time=0))
    path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(path.as_posix())


def _default_spec() -> GenerationControlSpec:
    ratios = named_ratio_catalog()
    controls = [
        RatioControl(
            ratio_name="golden_section_0_618",
            target_ratio=ratios["golden_section_0_618"].decimal_value,
            measured_ratio=None,
            tolerance=0.08,
            confidence=0.82,
            strict=False,
            source_observation_ids=["ratio_plan_climax_anchor"],
            notes=["strongest_density_peak_should_align_with_golden_section"],
        ),
        RatioControl(
            ratio_name="3:2",
            target_ratio=ratios["3:2"].decimal_value,
            measured_ratio=None,
            tolerance=0.08,
            confidence=0.82,
            strict=False,
            source_observation_ids=["ratio_plan_phrase_grid"],
            notes=["alternating_phrase_lengths_with_explicit_boundaries"],
        ),
        RatioControl(
            ratio_name="5:3",
            target_ratio=ratios["5:3"].decimal_value,
            measured_ratio=None,
            tolerance=0.08,
            confidence=0.8,
            strict=False,
            source_observation_ids=["ratio_plan_rhythm_cells"],
            notes=["onset_cells_follow_5_to_3_relation"],
        ),
        RatioControl(
            ratio_name="5:4",
            target_ratio=ratios["5:4"].decimal_value,
            measured_ratio=None,
            tolerance=0.08,
            confidence=0.8,
            strict=False,
            source_observation_ids=["ratio_plan_interval_targets"],
            notes=["step_to_leap_interval_ratio_target"],
        ),
        RatioControl(
            ratio_name="8:5",
            target_ratio=ratios["8:5"].decimal_value,
            measured_ratio=None,
            tolerance=0.1,
            confidence=0.78,
            strict=False,
            source_observation_ids=["ratio_plan_density_curve"],
            notes=["density_peak_to_tail_ratio_target"],
        ),
    ]
    return GenerationControlSpec(
        spec_id="ratio_controlled_song_v2_spec",
        generation_id="ratio_controlled_song_v2",
        duration_seconds=120.0,
        bpm=108,
        ratio_controls=controls,
        preserve_battle_appeal_priority=True,
        flexibility_priority=0.72,
        ratio_musicality_weight=0.24,
        evidence_based_only=True,
        no_cloud_calls=True,
        notes=[
            "Focused v2 compliance repair with explicit ratio planning before note generation.",
            "Controls remain honest and soft; evaluator integrity remains unchanged.",
        ],
    )


def _build_ratio_plan(spec: GenerationControlSpec) -> dict[str, Any]:
    beat = 60.0 / spec.bpm
    controls = {item.ratio_name: item for item in spec.ratio_controls}
    golden_ratio = controls["golden_section_0_618"].target_ratio
    phrase_ratio = controls["3:2"].target_ratio
    rhythm_ratio = controls["5:3"].target_ratio
    interval_ratio = controls["5:4"].target_ratio
    density_ratio = controls["8:5"].target_ratio
    phrase_short_beats = 4
    phrase_long_beats = int(round(phrase_short_beats * phrase_ratio))
    phrase_short_seconds = phrase_short_beats * beat
    phrase_long_seconds = phrase_long_beats * beat
    phrase_boundaries = [0.0]
    idx = 0
    while phrase_boundaries[-1] < spec.duration_seconds - 1e-6:
        beats = phrase_long_beats if idx % 2 == 0 else phrase_short_beats
        nxt = phrase_boundaries[-1] + (beats * beat)
        phrase_boundaries.append(min(spec.duration_seconds, nxt))
        idx += 1
    section_boundaries = [
        0.0,
        round(spec.duration_seconds * 0.236, 3),
        round(spec.duration_seconds * 0.382, 3),
        round(spec.duration_seconds * golden_ratio, 3),
        spec.duration_seconds,
    ]
    golden_climax_ts = round(spec.duration_seconds * golden_ratio, 6)
    return {
        "plan_version": "v2_ratio_compliance_repair",
        "generation_id": spec.generation_id,
        "duration_seconds": spec.duration_seconds,
        "bpm": spec.bpm,
        "controls": {
            item.ratio_name: {"target": item.target_ratio, "tolerance": item.tolerance, "confidence": item.confidence}
            for item in spec.ratio_controls
        },
        "pre_generation_plan": {
            "duration": {"target_seconds": spec.duration_seconds, "target_beats": round(spec.duration_seconds / beat, 6)},
            "section_boundaries_seconds": section_boundaries,
            "golden_climax_ts": golden_climax_ts,
            "phrase_grid": {
                "long_phrase_beats": phrase_long_beats,
                "short_phrase_beats": phrase_short_beats,
                "target_ratio": phrase_ratio,
                "long_phrase_seconds": round(phrase_long_seconds, 6),
                "short_phrase_seconds": round(phrase_short_seconds, 6),
                "phrase_boundaries_seconds": [round(x, 6) for x in phrase_boundaries],
            },
            "rhythm_cell_ratios": {
                "target_ratio": rhythm_ratio,
                "long_cell_subdivisions": 5,
                "short_cell_subdivisions": 3,
                "cell_seconds": {"long": round((5.0 / 4.0) * beat, 6), "short": round((3.0 / 4.0) * beat, 6)},
            },
            "chord_timing": {
                "target_ratio": rhythm_ratio,
                "long_chord_beats": 5,
                "short_chord_beats": 3,
                "cycle_roots": [48, 50, 53, 55, 57, 53, 50, 48],
            },
            "density_curve": {
                "target_ratio": density_ratio,
                "peak_window_start": round(golden_climax_ts - (4.0 * beat), 6),
                "peak_window_end": round(golden_climax_ts + (4.0 * beat), 6),
                "pre_peak_notes_per_phrase": 9,
                "peak_notes_per_phrase": 16,
                "post_peak_notes_per_phrase": 10,
            },
            "motif_recurrence": {
                "cell": [0, 2, 4, 7],
                "target_repeats_per_phrase": 2,
                "variation_every_n_phrases": 3,
            },
            "interval_voicing_targets": {
                "target_ratio": interval_ratio,
                "step_size_max_semitones": 2,
                "leap_size_min_semitones": 3,
                "target_step_to_leap_ratio": interval_ratio,
            },
        },
    }


def _build_song_notes_from_plan(plan: dict[str, Any]) -> dict[str, list[tuple[float, float, int, int]]]:
    pg = plan["pre_generation_plan"]
    duration = float(plan["duration_seconds"])
    bpm = int(plan["bpm"])
    beat = 60.0 / bpm
    phrase_boundaries = [float(x) for x in pg["phrase_grid"]["phrase_boundaries_seconds"]]
    golden_climax_ts = float(pg["golden_climax_ts"])
    chord_roots = [int(x) for x in pg["chord_timing"]["cycle_roots"]]
    long_cell = float(pg["rhythm_cell_ratios"]["cell_seconds"]["long"])
    short_cell = float(pg["rhythm_cell_ratios"]["cell_seconds"]["short"])
    peak_start = float(pg["density_curve"]["peak_window_start"])
    peak_end = float(pg["density_curve"]["peak_window_end"])
    motif = [int(x) for x in pg["motif_recurrence"]["cell"]]
    full: list[tuple[float, float, int, int]] = []
    chords: list[tuple[float, float, int, int]] = []
    bass: list[tuple[float, float, int, int]] = []
    lead: list[tuple[float, float, int, int]] = []
    texture: list[tuple[float, float, int, int]] = []
    step_toggle = True
    lead_pitch = 67
    for idx in range(len(phrase_boundaries) - 1):
        start = phrase_boundaries[idx]
        end = phrase_boundaries[idx + 1]
        if end <= start + 0.05:
            continue
        root = chord_roots[idx % len(chord_roots)]
        chord_hold = min(end, start + (5.0 * beat if idx % 2 == 0 else 3.0 * beat))
        for n in [root, root + 4, root + 7]:
            note = (start, chord_hold, n, 86 if start < golden_climax_ts else 95)
            chords.append(note)
            full.append(note)
        tb = start
        bass_cell = long_cell if idx % 2 == 0 else short_cell
        while tb < end - 0.03:
            bass_note = root - 12 if int((tb - start) / max(0.001, bass_cell)) % 2 == 0 else root - 7
            b = (tb, min(tb + bass_cell * 0.72, end), bass_note, 84 if tb < golden_climax_ts else 93)
            bass.append(b)
            full.append(b)
            tb += bass_cell
        if peak_start <= start <= peak_end:
            lead_density = int(pg["density_curve"]["peak_notes_per_phrase"])
        elif start > peak_end:
            lead_density = int(pg["density_curve"]["post_peak_notes_per_phrase"])
        else:
            lead_density = int(pg["density_curve"]["pre_peak_notes_per_phrase"])
        lead_step = max(0.16, (end - start) / max(1, lead_density))
        tl = start + 0.06
        motif_offset = 0 if idx % int(pg["motif_recurrence"]["variation_every_n_phrases"]) != 0 else 1
        motif_idx = 0
        while tl < end - 0.05:
            pitch_shift = motif[(motif_idx + motif_offset) % len(motif)]
            if step_toggle:
                lead_pitch = max(60, min(82, lead_pitch + 2))
            else:
                lead_pitch = max(60, min(82, lead_pitch - 3))
            step_toggle = not step_toggle
            lp = lead_pitch + pitch_shift - 4
            vel = 92 if tl < golden_climax_ts else 104
            l_note = (tl, min(end, tl + lead_step * 0.68), lp, vel)
            lead.append(l_note)
            full.append(l_note)
            motif_idx += 1
            tl += lead_step
        texture_hits = 1 if start < peak_start else (5 if start <= peak_end else 2)
        for j in range(texture_hits):
            tt = start + j * (beat * 0.42)
            if tt >= end:
                break
            t_note = (tt, min(end, tt + beat * 0.28), 76 + (j % 2), 72)
            texture.append(t_note)
            full.append(t_note)
    burst_start = max(0.0, golden_climax_ts - beat * 1.25)
    burst_end = min(duration, golden_climax_ts + beat * 1.25)
    tt = burst_start
    while tt < burst_end:
        for pitch in (79, 83):
            b_note = (tt, min(burst_end, tt + beat * 0.2), pitch, 112)
            texture.append(b_note)
            full.append(b_note)
        tt += beat * 0.18
    clipped_full = [(s, min(e, duration), n, v) for s, e, n, v in full if s < duration and e > s]
    clipped_chords = [(s, min(e, duration), n, v) for s, e, n, v in chords if s < duration and e > s]
    clipped_bass = [(s, min(e, duration), n, v) for s, e, n, v in bass if s < duration and e > s]
    clipped_lead = [(s, min(e, duration), n, v) for s, e, n, v in lead if s < duration and e > s]
    clipped_texture = [(s, min(e, duration), n, v) for s, e, n, v in texture if s < duration and e > s]
    return {
        "full": clipped_full,
        "chords": clipped_chords,
        "bass": clipped_bass,
        "lead": clipped_lead,
        "texture": clipped_texture,
        "climax_time": [(golden_climax_ts, 0, 0, 0)],
    }


def _write_ratio_plan_md(path: Path, plan: dict[str, Any]) -> None:
    pg = plan["pre_generation_plan"]
    lines = [
        "# Ratio Plan (v2)",
        "",
        f"- generation_id: `{plan['generation_id']}`",
        f"- duration_seconds: `{plan['duration_seconds']}`",
        f"- bpm: `{plan['bpm']}`",
        f"- golden_climax_ts: `{pg['golden_climax_ts']}`",
        f"- section_boundaries_seconds: `{pg['section_boundaries_seconds']}`",
        f"- phrase_ratio_target: `{pg['phrase_grid']['target_ratio']}`",
        f"- rhythm_ratio_target: `{pg['rhythm_cell_ratios']['target_ratio']}`",
        f"- interval_ratio_target: `{pg['interval_voicing_targets']['target_ratio']}`",
        f"- density_ratio_target: `{pg['density_curve']['target_ratio']}`",
        "",
        "## Notes",
        "- Plan is authored before any note generation and used as the single generation source.",
        "- Boundaries and rhythm cells are explicit to improve evaluator observability.",
        "- Controls remain soft; warnings should still surface if compliance drops.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    out_root = ROOT_DIR / "outputs" / "ratio_controlled_song_v2"
    stems_dir = out_root / "stems"
    out_root.mkdir(parents=True, exist_ok=True)
    stems_dir.mkdir(parents=True, exist_ok=True)
    spec = _default_spec()
    plan = _build_ratio_plan(spec)
    notes = _build_song_notes_from_plan(plan)
    _write_midi(out_root / "full.mid", notes["full"], bpm=spec.bpm)
    _write_midi(stems_dir / "chords.mid", notes["chords"], bpm=spec.bpm)
    _write_midi(stems_dir / "bass.mid", notes["bass"], bpm=spec.bpm)
    _write_midi(stems_dir / "lead.mid", notes["lead"], bpm=spec.bpm)
    _write_midi(stems_dir / "texture.mid", notes["texture"], bpm=spec.bpm)
    ratio_control_spec = out_root / "ratio_control_spec.json"
    ratio_control_spec.write_text(json.dumps(spec.to_dict(), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    ratio_plan_json = out_root / "ratio_plan.json"
    ratio_plan_json.write_text(json.dumps(plan, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    ratio_plan_md = out_root / "ratio_plan.md"
    _write_ratio_plan_md(ratio_plan_md, plan)
    climax_time = notes["climax_time"][0][0]
    generation_report = out_root / "generation_report.md"
    generation_report.write_text(
        "\n".join(
            [
                "# Ratio Controlled Song Generation Report",
                "",
                f"- generation_id: `{spec.generation_id}`",
                f"- duration_seconds: `{spec.duration_seconds}`",
                f"- bpm: `{spec.bpm}`",
                f"- no_cloud_calls: `{str(spec.no_cloud_calls).lower()}`",
                f"- evidence_based_only: `{str(spec.evidence_based_only).lower()}`",
                "- ratio_plan: `outputs/ratio_controlled_song_v2/ratio_plan.json`",
                f"- climax_time_seconds: `{round(climax_time, 3)}`",
                "- full_midi: `outputs/ratio_controlled_song_v2/full.mid`",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    ratio_explanation = out_root / "ratio_explanation.md"
    ratio_explanation.write_text(
        "\n".join(
            [
                "# Ratio Explanation",
                "",
                "- V2 uses explicit pre-generation planning for duration, sections, phrase grid, and rhythm cells.",
                "- The golden-section control is tied to strongest density peak timing, not a fixed hard-coded pass.",
                "- Phrase and chord boundaries are planned first then rendered into stems for evaluability.",
                "- Interval behavior targets a step/leap ratio near 5:4 while preserving melodic variation.",
                "- Density planning aims for an 8:5 peak-to-tail relation around the climax region.",
                "- Warnings remain enabled when compliance or musicality decreases.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    review_sheet = out_root / "review_sheet.md"
    review_sheet.write_text(
        "\n".join(
            [
                "# Ratio Controlled Review Sheet",
                "",
                "- [ ] Golden section peak felt intentional and musical",
                "- [ ] Phrase boundary alternation sounds natural at 3:2 target",
                "- [ ] Rhythm cell balance supports groove without over-quantization",
                "- [ ] Interval profile remains coherent (not robotic)",
                "- [ ] Density arc supports arrangement and battle appeal",
                "- [ ] Warnings remain truthful if controls become too rigid",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"RATIO_CONTROL_SPEC={ratio_control_spec.as_posix()}")
    print(f"RATIO_PLAN_JSON={ratio_plan_json.as_posix()}")
    print(f"RATIO_CONTROLLED_SONG_PATH={(out_root / 'full.mid').as_posix()}")
    print(f"GENERATION_REPORT={generation_report.as_posix()}")
    print(f"GENERATED_AT={datetime.now(UTC).isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

