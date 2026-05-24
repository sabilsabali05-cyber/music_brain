from __future__ import annotations

import json
import random
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mido import Message, MetaMessage, MidiFile, MidiTrack, second2tick

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.taste_learning.composition_ranker import load_model, rank_candidates  # noqa: E402


def _write_midi(path: Path, notes: list[tuple[float, float, int, int]], bpm: int = 100) -> None:
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


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT_DIR.resolve()).as_posix()
    except Exception:  # noqa: BLE001
        return path.as_posix()


def _candidate_notes(seed: int, bars: int = 8) -> list[tuple[float, float, int, int]]:
    rng = random.Random(seed)
    notes: list[tuple[float, float, int, int]] = []
    t = 0.0
    beat = 0.5
    for _ in range(bars * 8):
        note = rng.choice([48, 50, 52, 55, 57, 59, 60, 62, 64, 67, 69])
        duration = rng.choice([0.25, 0.5, 0.75])
        vel = rng.randint(70, 112)
        notes.append((t, t + duration, note, vel))
        t += beat
    return notes


def _features(notes: list[tuple[float, float, int, int]]) -> dict[str, float]:
    if not notes:
        return {"musicality_score": 0.0, "groove_score": 0.0, "harmony_score": 0.0, "density_score": 0.0, "variety_score": 0.0}
    pitches = [n[2] for n in notes]
    durations = [max(0.01, n[1] - n[0]) for n in notes]
    unique_pc = len({p % 12 for p in pitches}) / 12.0
    density = min(1.0, len(notes) / 96.0)
    long_ratio = sum(1 for d in durations if d >= 0.5) / len(durations)
    leap_ratio = sum(1 for i in range(1, len(pitches)) if abs(pitches[i] - pitches[i - 1]) > 7) / max(1, len(pitches) - 1)
    groove = max(0.0, 1.0 - abs(0.5 - long_ratio))
    harmony = min(1.0, unique_pc + 0.3)
    variety = min(1.0, len(set(pitches)) / 10.0)
    musicality = max(0.0, min(1.0, 0.45 * groove + 0.35 * harmony + 0.2 * (1.0 - leap_ratio)))
    return {
        "musicality_score": musicality,
        "groove_score": groove,
        "harmony_score": harmony,
        "density_score": density,
        "variety_score": variety,
    }


def main() -> int:
    generation_id = "music_understanding_loop_v1"
    out_root = ROOT_DIR / "outputs" / generation_id
    candidates_dir = out_root / "candidates"
    selected_dir = out_root / "selected"
    stems_dir = out_root / "stems"
    report_json = ROOT_DIR / "reports" / "taste_learning" / "ranked_midi_candidates_report.json"
    report_md = ROOT_DIR / "reports" / "taste_learning" / "ranked_midi_candidates_report.md"
    candidates_dir.mkdir(parents=True, exist_ok=True)
    selected_dir.mkdir(parents=True, exist_ok=True)
    stems_dir.mkdir(parents=True, exist_ok=True)
    model_payload = load_model(ROOT_DIR / "artifacts" / "taste_learning" / "composition_ranker" / "model.json")

    candidate_rows: list[dict[str, Any]] = []
    for idx in range(8):
        candidate_id = f"candidate_{idx+1:02d}"
        midi_path = candidates_dir / f"{candidate_id}.mid"
        notes = _candidate_notes(1000 + idx)
        _write_midi(midi_path, notes, bpm=96 + idx)
        features = _features(notes)
        candidate_rows.append(
            {
                "generation_id": generation_id,
                "candidate_id": candidate_id,
                "midi_path": _repo_rel(midi_path),
                **features,
            }
        )

    ranked = rank_candidates(candidate_rows, model_payload)
    selected = ranked[0] if ranked else {}
    selected_path = str(selected.get("midi_path", "")) if selected else ""
    if selected_path:
        selected_abs = ROOT_DIR / selected_path
        (selected_dir / "selected_candidate.mid").write_bytes(selected_abs.read_bytes())
        (stems_dir / "harmony.mid").write_bytes(selected_abs.read_bytes())
        (stems_dir / "bass.mid").write_bytes(selected_abs.read_bytes())
        (stems_dir / "lead.mid").write_bytes(selected_abs.read_bytes())

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "generation_id": generation_id,
        "candidates_generated": len(ranked),
        "trained_ranker_used": model_payload.get("model_type") == "tiny_linear_preference_ranker",
        "heuristic_ranker_used": model_payload.get("model_type") != "tiny_linear_preference_ranker",
        "selected_candidate_id": selected.get("candidate_id", ""),
        "selected_candidate_path": selected_path,
        "ranked_candidates": ranked,
        "policy": {
            "no_cloud_calls": True,
            "wav_rendering_attempted": False,
            "chordpotion_variant_created": False,
        },
    }
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    report_md.write_text(
        "\n".join(
            [
                "# Ranked MIDI Candidates Report",
                "",
                f"- generation_id: `{generation_id}`",
                f"- candidates_generated: `{payload['candidates_generated']}`",
                f"- trained_ranker_used: `{str(payload['trained_ranker_used']).lower()}`",
                f"- heuristic_ranker_used: `{str(payload['heuristic_ranker_used']).lower()}`",
                f"- selected_candidate_id: `{payload['selected_candidate_id'] or 'none'}`",
                f"- selected_candidate_path: `{payload['selected_candidate_path'] or 'none'}`",
                "- wav_rendering_attempted: `false`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "generation_report.json").write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"CANDIDATES_GENERATED={payload['candidates_generated']}")
    print(f"SELECTED_CANDIDATE_PATH={payload['selected_candidate_path'] or 'none'}")
    print(f"TRAINED_RANKER_USED={str(payload['trained_ranker_used']).lower()}")
    print(f"HEURISTIC_RANKER_USED={str(payload['heuristic_ranker_used']).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
