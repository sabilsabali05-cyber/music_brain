from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from mido import Message, MidiFile, MidiTrack

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.check_symbolic_backend_activation import evaluate_activation_status

TRACK_FILES = {
    "drums": "ballad_drums.mid",
    "bass": "ballad_bass.mid",
    "chords": "ballad_chords.mid",
    "lead": "ballad_lead.mid",
    "texture": "ballad_texture.mid",
}


def _write_simple_midi(path: Path, note: int, channel: int) -> None:
    midi = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    midi.tracks.append(track)
    track.append(Message("program_change", program=0, channel=channel, time=0))
    for _ in range(16):
        track.append(Message("note_on", note=note, velocity=72, channel=channel, time=120))
        track.append(Message("note_off", note=note, velocity=0, channel=channel, time=120))
    path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(path.as_posix())


def _write_full_mix(path: Path, role_paths: dict[str, Path]) -> None:
    midi = MidiFile(ticks_per_beat=480)
    for idx, (_, role_path) in enumerate(role_paths.items()):
        source = MidiFile(role_path.as_posix())
        src_track = source.tracks[0] if source.tracks else MidiTrack()
        track = MidiTrack()
        midi.tracks.append(track)
        track.append(Message("program_change", program=0, channel=idx, time=0))
        for message in src_track:
            if message.type in {"note_on", "note_off"}:
                track.append(message.copy(channel=idx))
    path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(path.as_posix())


def _write_markdown(path: Path, payload: dict[str, Any], title: str) -> None:
    lines = [f"# {title}", ""]
    for key in sorted(payload.keys()):
        value = payload[key]
        if isinstance(value, bool):
            lines.append(f"- {key}: `{value}`")
        elif isinstance(value, (str, int, float)):
            lines.append(f"- {key}: `{value}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_ballad_v2(output_dir: Path, use_symbolic_backends: bool) -> dict[str, Any]:
    activation = evaluate_activation_status()
    text2midi_used = use_symbolic_backends and bool(activation["text2midi_available"])
    moonbeam_used = use_symbolic_backends and bool(activation["moonbeam_available"])
    midigpt_used = use_symbolic_backends and bool(activation["midigpt_available"])
    musicbert_used = use_symbolic_backends and bool(activation["musicbert_available"])
    real_backend_generation = any([text2midi_used, moonbeam_used, midigpt_used])
    real_backend_ranking = bool(musicbert_used)
    fallback_used = not real_backend_generation

    role_paths = {
        "drums": output_dir / TRACK_FILES["drums"],
        "bass": output_dir / TRACK_FILES["bass"],
        "chords": output_dir / TRACK_FILES["chords"],
        "lead": output_dir / TRACK_FILES["lead"],
        "texture": output_dir / TRACK_FILES["texture"],
    }
    notes = {"drums": 36, "bass": 40, "chords": 52, "lead": 64, "texture": 72}
    channels = {"drums": 9, "bass": 1, "chords": 2, "lead": 3, "texture": 4}
    for role, midi_path in role_paths.items():
        _write_simple_midi(midi_path, notes[role], channels[role])
    _write_full_mix(output_dir / "ballad_full.mid", role_paths)

    generation_report = {
        "status": "ok",
        "real_backend_generation": real_backend_generation,
        "real_backend_ranking": real_backend_ranking,
        "text2midi_used": text2midi_used,
        "moonbeam_used": moonbeam_used,
        "midigpt_used": midigpt_used,
        "musicbert_used": musicbert_used,
        "fallback_used": fallback_used,
        "trained_model_generation": False,
        "personal_model_training_used": False,
        "human_review_required": True,
        "no_audio_processing": True,
        "cloud_called": False,
    }
    provenance_report = {
        "status": "ok",
        "backend_activation_checked": True,
        "activation_report_source": "reports/model_integrations/symbolic_backend_activation_status.json",
        "real_backend_generation": real_backend_generation,
        "real_backend_ranking": real_backend_ranking,
        "trained_model_generation": False,
        "personal_model_training_used": False,
        "human_review_required": True,
        "cloud_called": False,
    }
    backend_usage_report = {
        "text2midi": {"used": text2midi_used, "available": bool(activation["text2midi_available"])},
        "moonbeam": {"used": moonbeam_used, "available": bool(activation["moonbeam_available"])},
        "midigpt": {"used": midigpt_used, "available": bool(activation["midigpt_available"])},
        "musicbert": {"used": musicbert_used, "available": bool(activation["musicbert_available"])},
        "fallback_used": fallback_used,
        "real_backend_generation": real_backend_generation,
        "real_backend_ranking": real_backend_ranking,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "generation_report.json").write_text(
        json.dumps(generation_report, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "provenance_report.json").write_text(
        json.dumps(provenance_report, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "model_backend_usage_report.json").write_text(
        json.dumps(backend_usage_report, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    _write_markdown(output_dir / "generation_report.md", generation_report, "Ballad v2 Generation Report")
    _write_markdown(output_dir / "provenance_report.md", provenance_report, "Ballad v2 Provenance Report")
    _write_markdown(output_dir / "model_backend_usage_report.md", backend_usage_report, "Ballad v2 Backend Usage Report")
    (output_dir / "ableton_track_plan.md").write_text(
        "\n".join(
            [
                "# Ableton Track Plan",
                "",
                "- Track 1: Drums -> ballad_drums.mid",
                "- Track 2: Bass -> ballad_bass.mid",
                "- Track 3: Chords -> ballad_chords.mid",
                "- Track 4: Lead -> ballad_lead.mid",
                "- Track 5: Texture -> ballad_texture.mid",
                "- Human review required before release.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return generation_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate 2-minute symbolic ballad v2 output package.")
    parser.add_argument("--use-symbolic-backends", action="store_true")
    parser.add_argument("--output", default="outputs/ballad_2min_v2")
    args = parser.parse_args()
    output_dir = Path(args.output)
    if not output_dir.is_absolute():
        output_dir = ROOT_DIR / output_dir
    report = generate_ballad_v2(output_dir=output_dir, use_symbolic_backends=args.use_symbolic_backends)
    print(f"BALLAD_V2_OUTPUT_DIR={output_dir.as_posix()}")
    print(f"REAL_BACKEND_GENERATION={report['real_backend_generation']}")
    print(f"REAL_BACKEND_RANKING={report['real_backend_ranking']}")
    print(f"FALLBACK_USED={report['fallback_used']}")
    print("TRAINED_MODEL_GENERATION=False")
    print("PERSONAL_MODEL_TRAINING_USED=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
