from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from mido import MidiFile

ROOT_DIR = Path(__file__).resolve().parent.parent


def _collect_notes(path: Path) -> list[int]:
    if not path.exists():
        return []
    midi = MidiFile(path.as_posix())
    notes: list[int] = []
    for track in midi.tracks:
        for msg in track:
            if msg.type == "note_on" and msg.velocity > 0:
                notes.append(int(msg.note))
    return notes


def _random_note_penalty(notes: list[int]) -> float:
    if len(notes) < 3:
        return 1.0
    big_jumps = 0
    for i in range(len(notes) - 1):
        if abs(notes[i + 1] - notes[i]) > 11:
            big_jumps += 1
    return min(1.0, big_jumps / max(1, len(notes) - 1))


def _voice_leading_score(notes: list[int]) -> float:
    if len(notes) < 3:
        return 0.0
    smooth = 0
    for i in range(len(notes) - 1):
        if abs(notes[i + 1] - notes[i]) <= 5:
            smooth += 1
    return smooth / max(1, len(notes) - 1)


def _chord_movement_score(notes: list[int]) -> float:
    if len(notes) < 4:
        return 0.0
    unique = len(set(n % 12 for n in notes))
    return min(1.0, unique / 8.0)


def main() -> int:
    current = ROOT_DIR / "outputs" / "theory_conditioned_generation_v1"
    baseline_candidates = [
        ROOT_DIR / "outputs" / "ballad_2min_v1" / "ballad_full.mid",
        ROOT_DIR / "outputs" / "through_composed_story_100bpm_v4" / "full.mid",
        ROOT_DIR / "outputs" / "through_composed_story_100bpm_v5" / "full.mid",
    ]
    generated_files = [
        current / "harmony_first_piano_skeleton.mid",
        current / "weird_but_musical_progression.mid",
        current / "rhythm_motif_study.mid",
    ]
    generated_notes = []
    for path in generated_files:
        generated_notes.extend(_collect_notes(path))
    baseline_notes = []
    for path in baseline_candidates:
        baseline_notes.extend(_collect_notes(path))
    gen_random = _random_note_penalty(generated_notes)
    base_random = _random_note_penalty(baseline_notes) if baseline_notes else 1.0
    gen_voice = _voice_leading_score(generated_notes)
    base_voice = _voice_leading_score(baseline_notes) if baseline_notes else 0.0
    gen_chord = _chord_movement_score(generated_notes)
    base_chord = _chord_movement_score(baseline_notes) if baseline_notes else 0.0
    weirdness_preserved = any(abs(generated_notes[i + 1] - generated_notes[i]) in {6, 7, 8} for i in range(max(0, len(generated_notes) - 1)))
    improved = (gen_random <= base_random) and (gen_voice >= base_voice) and (gen_chord >= base_chord)
    eval_payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "baseline_found": any(path.exists() for path in baseline_candidates),
        "metrics": {
            "random_note_penalty": {"baseline": round(base_random, 4), "theory_conditioned": round(gen_random, 4), "improved": gen_random <= base_random},
            "voice_leading_score": {"baseline": round(base_voice, 4), "theory_conditioned": round(gen_voice, 4), "improved": gen_voice >= base_voice},
            "chord_movement_score": {"baseline": round(base_chord, 4), "theory_conditioned": round(gen_chord, 4), "improved": gen_chord >= base_chord},
            "weirdness_preserved_musically": weirdness_preserved,
        },
        "theory_conditioning_improved_generation_metrics": improved,
        "remaining_failures": [
            "sparse source labels limit deep harmonic certainty",
            "motif extraction still proxy-based from metadata, not dense symbolic parsing",
        ],
        "policy": {"cloud_called": False, "model_training_used": False, "raw_media_processed": False},
    }
    report_json = ROOT_DIR / "reports" / "music_theory" / "theory_conditioned_generation_eval.json"
    report_md = ROOT_DIR / "reports" / "music_theory" / "theory_conditioned_generation_eval.md"
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(eval_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    report_md.write_text(
        "# Theory Conditioned Generation Evaluation\n\n"
        f"- theory_conditioning_improved_generation_metrics: `{improved}`\n"
        f"- random_note_penalty improved: `{eval_payload['metrics']['random_note_penalty']['improved']}`\n"
        f"- voice_leading_score improved: `{eval_payload['metrics']['voice_leading_score']['improved']}`\n"
        f"- chord_movement_score improved: `{eval_payload['metrics']['chord_movement_score']['improved']}`\n"
        f"- weirdness preserved musically: `{weirdness_preserved}`\n",
        encoding="utf-8",
    )
    print(f"THEORY_EVAL_JSON={report_json.as_posix()}")
    print(f"THEORY_EVAL_MD={report_md.as_posix()}")
    print(f"THEORY_CONDITIONING_IMPROVED={improved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
