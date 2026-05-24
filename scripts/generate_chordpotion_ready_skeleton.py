from __future__ import annotations

import json
import sys
from pathlib import Path

from mido import Message, MetaMessage, MidiFile, MidiTrack, second2tick

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.local_rendering.reaper_backend import load_local_render_config  # noqa: E402

GENERATION_ID = "chordpotion_generation_v1"


def _write_simple_midi(path: Path, notes: list[tuple[float, float, int, int]], channel: int = 0, bpm: int = 100) -> None:
    midi = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    midi.tracks.append(track)
    tempo = int(round(60_000_000 / max(1, bpm)))
    track.append(MetaMessage("set_tempo", tempo=tempo, time=0))
    timeline: list[tuple[float, Message]] = []
    for start, end, note, velocity in notes:
        timeline.append((start, Message("note_on", note=note, velocity=velocity, channel=channel, time=0)))
        timeline.append((end, Message("note_off", note=note, velocity=0, channel=channel, time=0)))
    timeline.sort(key=lambda item: (item[0], 0 if item[1].type == "note_off" else 1))
    previous = 0.0
    for when, msg in timeline:
        delta = int(round(second2tick(max(0.0, when - previous), midi.ticks_per_beat, tempo)))
        track.append(msg.copy(time=max(0, delta)))
        previous = when
    track.append(MetaMessage("end_of_track", time=0))
    path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(str(path))


def _build_harmony_notes() -> list[tuple[float, float, int, int]]:
    # Strong harmonic movement with low clutter and 2-5 note voicings.
    return [
        (0.0, 1.2, 60, 84), (0.0, 1.2, 64, 80), (0.0, 1.2, 67, 78),
        (1.2, 2.4, 62, 84), (1.2, 2.4, 65, 79), (1.2, 2.4, 69, 80), (1.2, 2.4, 72, 74),
        (2.4, 3.6, 57, 84), (2.4, 3.6, 60, 80), (2.4, 3.6, 64, 78),
        (3.6, 4.8, 59, 84), (3.6, 4.8, 62, 79), (3.6, 4.8, 65, 78), (3.6, 4.8, 69, 74),
    ]


def _build_bass_notes() -> list[tuple[float, float, int, int]]:
    return [
        (0.0, 0.9, 36, 90), (0.9, 1.2, 43, 82),
        (1.2, 2.1, 38, 90), (2.1, 2.4, 45, 82),
        (2.4, 3.3, 33, 90), (3.3, 3.6, 40, 82),
        (3.6, 4.5, 35, 90), (4.5, 4.8, 42, 82),
    ]


def _build_lead_guide_notes() -> list[tuple[float, float, int, int]]:
    return [
        (0.0, 0.6, 72, 76), (0.8, 1.2, 74, 74),
        (1.2, 1.8, 76, 77), (2.0, 2.4, 77, 74),
        (2.4, 3.0, 71, 76), (3.2, 3.6, 72, 74),
        (3.6, 4.2, 74, 76), (4.3, 4.8, 76, 74),
    ]


def _write_reports(output_root: Path, bpm: int) -> None:
    (output_root / "generation_report.md").write_text(
        "\n".join(
            [
                "# ChordPotion Ready Skeleton Report",
                "",
                f"- generation_id: `{GENERATION_ID}`",
                f"- bpm: `{bpm}`",
                "- cloud_calls: false",
                "- model_training: false",
                "- model_downloads: false",
                "- plugin_downloads: false",
                "- generation_rules_applied: strong_movement, low_clutter, voicings_2_to_5_notes",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (output_root / "provenance_report.md").write_text(
        "\n".join(
            [
                "# Provenance Report",
                "",
                "- All MIDI files were generated locally by deterministic script logic.",
                "- No cloud APIs, model training, or unauthorized audio sources were used.",
                "- No private plugin paths are written to tracked reports.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (output_root / "review_sheet.md").write_text(
        "\n".join(
            [
                "# Review Sheet",
                "",
                "- Confirm harmonic movement is clearly directional.",
                "- Confirm skeleton remains uncluttered and leaves mix space.",
                "- Confirm chord voicings stay between 2 and 5 notes.",
                "- Confirm bass supports root motion without masking harmony.",
                "- Confirm lead guide indicates phrase contour without over-arranging.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> int:
    output_root = ROOT_DIR / "outputs" / GENERATION_ID
    output_root.mkdir(parents=True, exist_ok=True)
    config = load_local_render_config(ROOT_DIR / "config" / "local_render_config.local.json")
    bpm = int(config.get("chordpotion_default_bpm", 100) or 100)
    if bpm <= 0:
        bpm = 100

    _write_simple_midi(output_root / "harmony_skeleton.mid", _build_harmony_notes(), channel=0, bpm=bpm)
    _write_simple_midi(output_root / "bass.mid", _build_bass_notes(), channel=1, bpm=bpm)
    _write_simple_midi(output_root / "lead_guide.mid", _build_lead_guide_notes(), channel=2, bpm=bpm)
    _write_reports(output_root, bpm)
    (output_root / "generation_report.json").write_text(
        json.dumps({"generation_id": GENERATION_ID, "bpm": bpm, "safe_local_mode": True}, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    print(f"OUTPUT_DIR={output_root.as_posix()}")
    print("CREATED=harmony_skeleton.mid,bass.mid,lead_guide.mid,generation_report.md,provenance_report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

