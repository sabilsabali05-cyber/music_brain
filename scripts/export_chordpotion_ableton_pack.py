from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Export an assisted Ableton pack for ChordPotion workflow.")
    parser.add_argument("--generation-id", default="chordpotion_generation_v1")
    parser.add_argument("--reason", default="chordpotion_or_reaper_unavailable")
    args = parser.parse_args()

    output_root = ROOT_DIR / "outputs" / args.generation_id
    pack_root = ROOT_DIR / "outputs" / "render_ready_packs" / f"{args.generation_id}_chordpotion"
    midi_root = pack_root / "midi"
    midi_root.mkdir(parents=True, exist_ok=True)

    for name in ("harmony_skeleton.mid", "bass.mid", "lead_guide.mid", "transformed_harmony.mid"):
        source = output_root / name
        if source.exists():
            (midi_root / name).write_bytes(source.read_bytes())

    (pack_root / "setup_instructions.md").write_text(
        "\n".join(
            [
                "# ChordPotion Ableton Assisted Setup",
                "",
                "1. Create a new empty Ableton project (do not modify existing real projects).",
                "2. Import `midi/harmony_skeleton.mid`, `midi/bass.mid`, and `midi/lead_guide.mid`.",
                "3. Insert ChordPotion as MIDI FX only if locally available/verified.",
                "4. Route ChordPotion output to instrument tracks and capture transformed MIDI manually.",
                "5. Export final WAV as `renders/chordpotion_generation_v1/final.wav`.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (pack_root / "review_sheet.md").write_text(
        "\n".join(
            [
                "# Review Sheet",
                "",
                "- Confirm no private absolute paths are pasted into project notes.",
                "- Confirm transformed MIDI was captured manually if plugin was available.",
                "- Confirm WAV export only after audible/technical verification.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (pack_root / "report.json").write_text(
        json.dumps(
            {
                "generation_id": args.generation_id,
                "reason": args.reason,
                "pack_path": pack_root.relative_to(ROOT_DIR).as_posix(),
                "wav_rendered": False,
                "render_plan_only": True,
            },
            indent=2,
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"ASSISTED_PACK={pack_root.relative_to(ROOT_DIR).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

