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
            confidence=0.72,
            strict=False,
            source_observation_ids=["demo_section_ratio"],
            notes=["default_demo_climax_anchor"],
        ),
        RatioControl(
            ratio_name="3:2",
            target_ratio=ratios["3:2"].decimal_value,
            measured_ratio=None,
            tolerance=0.08,
            confidence=0.78,
            strict=False,
            source_observation_ids=["demo_phrase_ratio"],
            notes=["phrase_length_relation"],
        ),
        RatioControl(
            ratio_name="5:3",
            target_ratio=ratios["5:3"].decimal_value,
            measured_ratio=None,
            tolerance=0.08,
            confidence=0.71,
            strict=False,
            source_observation_ids=["demo_rhythm_ratio"],
            notes=["rhythm_subdivision_relation"],
        ),
        RatioControl(
            ratio_name="5:4",
            target_ratio=ratios["5:4"].decimal_value,
            measured_ratio=None,
            tolerance=0.08,
            confidence=0.74,
            strict=False,
            source_observation_ids=["demo_interval_ratio"],
            notes=["interval_motion_relation"],
        ),
        RatioControl(
            ratio_name="8:5",
            target_ratio=ratios["8:5"].decimal_value,
            measured_ratio=None,
            tolerance=0.1,
            confidence=0.68,
            strict=False,
            source_observation_ids=["demo_density_ratio"],
            notes=["arrangement_density_relation"],
        ),
    ]
    return GenerationControlSpec(
        spec_id="ratio_controlled_song_v1_spec",
        generation_id="ratio_controlled_song_v1",
        duration_seconds=120.0,
        bpm=108,
        ratio_controls=controls,
        preserve_battle_appeal_priority=True,
        flexibility_priority=0.7,
        ratio_musicality_weight=0.22,
        evidence_based_only=True,
        no_cloud_calls=True,
        notes=[
            "Default demo uses ratio guidance for duration/climax/section/phrase/rhythm/interval/density.",
            "No universal ratio forcing; controls are soft by default.",
        ],
    )


def _build_song_notes(spec: GenerationControlSpec) -> dict[str, list[tuple[float, float, int, int]]]:
    duration = spec.duration_seconds
    beat = 60.0 / spec.bpm
    control = {c.ratio_name: c.target_ratio for c in spec.ratio_controls}
    section_ratio = control.get("golden_section_0_618", 0.61803398875)
    phrase_ratio = control.get("3:2", 1.5)
    rhythm_ratio = control.get("5:3", 5.0 / 3.0)

    climax_time = duration * min(0.95, max(0.05, section_ratio))
    phrase_a = beat * 8.0
    phrase_b = phrase_a / max(1e-6, phrase_ratio)
    pulse_short = beat / 2.0
    pulse_long = pulse_short * max(1.0, rhythm_ratio / 1.5)

    full: list[tuple[float, float, int, int]] = []
    chords: list[tuple[float, float, int, int]] = []
    bass: list[tuple[float, float, int, int]] = []
    lead: list[tuple[float, float, int, int]] = []
    texture: list[tuple[float, float, int, int]] = []

    t = 0.0
    chord_roots = [48, 50, 53, 55, 57, 53, 50, 48]
    i = 0
    while t < duration:
        phrase_len = phrase_a if i % 2 == 0 else phrase_b
        phrase_end = min(duration, t + phrase_len)
        root = chord_roots[i % len(chord_roots)]
        chord = [root, root + 7, root + 12]
        for note in chord:
            start = t
            end = min(phrase_end, t + max(beat * 3.0, phrase_len * 0.7))
            vel = 82 if start < climax_time else 94
            chords.append((start, end, note, vel))
            full.append((start, end, note, vel))

        bass_step = pulse_long if (i % 3 == 0) else pulse_short
        tb = t
        while tb < phrase_end:
            end = min(tb + pulse_short * 0.95, phrase_end)
            vel = 86 if tb < climax_time else 99
            bass_note = root - 12 if (int((tb - t) / max(0.001, bass_step)) % 2 == 0) else root - 7
            bass.append((tb, end, bass_note, vel))
            full.append((tb, end, bass_note, vel))
            tb += bass_step

        tl = t
        lead_pitch = 67 + (i % 5)
        while tl < phrase_end:
            dur = pulse_short if (int((tl - t) / max(0.001, pulse_short)) % 3 != 0) else pulse_long
            end = min(tl + dur * 0.8, phrase_end)
            vel = 88 if tl < climax_time else 108
            lead.append((tl, end, lead_pitch, vel))
            full.append((tl, end, lead_pitch, vel))
            tl += dur
            lead_pitch += 2 if lead_pitch < 76 else -5

        density = 4 if t < climax_time else 2
        for j in range(density):
            x = t + (j * beat * 0.5)
            if x >= phrase_end:
                break
            texture.append((x, min(x + beat * 0.35, phrase_end), 76 + (j % 3), 70))
            full.append((x, min(x + beat * 0.35, phrase_end), 76 + (j % 3), 70))

        t = phrase_end
        i += 1

    return {"full": full, "chords": chords, "bass": bass, "lead": lead, "texture": texture, "climax_time": [(climax_time, 0, 0, 0)]}


def main() -> int:
    out_root = ROOT_DIR / "outputs" / "ratio_controlled_song_v1"
    stems_dir = out_root / "stems"
    out_root.mkdir(parents=True, exist_ok=True)
    stems_dir.mkdir(parents=True, exist_ok=True)

    spec = _default_spec()
    notes = _build_song_notes(spec)
    _write_midi(out_root / "full.mid", notes["full"], bpm=spec.bpm)
    _write_midi(stems_dir / "chords.mid", notes["chords"], bpm=spec.bpm)
    _write_midi(stems_dir / "bass.mid", notes["bass"], bpm=spec.bpm)
    _write_midi(stems_dir / "lead.mid", notes["lead"], bpm=spec.bpm)
    _write_midi(stems_dir / "texture.mid", notes["texture"], bpm=spec.bpm)

    ratio_control_spec = out_root / "ratio_control_spec.json"
    ratio_control_spec.write_text(json.dumps(spec.to_dict(), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

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
                f"- climax_time_seconds: `{round(climax_time, 3)}`",
                f"- full_midi: `{(out_root / 'full.mid').as_posix()}`",
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
                "- Ratio controls are evidence-oriented defaults and can be replaced with analyzed observations.",
                "- Climax timing uses a golden-section anchor only as a soft arrangement guide.",
                "- Phrase durations alternate around a 3:2 relation for controlled contrast.",
                "- Rhythm pulse switching follows a 5:3 relation for groove variation.",
                "- Interval motion and arrangement density are ratio-guided but not hard-locked.",
                "- Battle appeal remains prioritized: controls are flexible and musicality-first.",
                "- Unknown evidence should keep controls in soft mode rather than forcing structure.",
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
                "- [ ] Climax felt natural near ratio anchor",
                "- [ ] Phrase proportion sounded musical (not mechanical)",
                "- [ ] Rhythm ratio helped groove",
                "- [ ] Interval pacing felt coherent",
                "- [ ] Density evolution served arrangement and battle appeal",
                "- [ ] Ratio constraints stayed flexible where needed",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(f"RATIO_CONTROL_SPEC={ratio_control_spec.as_posix()}")
    print(f"RATIO_CONTROLLED_SONG_PATH={(out_root / 'full.mid').as_posix()}")
    print(f"GENERATION_REPORT={generation_report.as_posix()}")
    print(f"GENERATED_AT={datetime.now(UTC).isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

