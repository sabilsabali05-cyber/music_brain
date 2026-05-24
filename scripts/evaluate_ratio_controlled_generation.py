from __future__ import annotations

import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mido import MidiFile

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _midi_notes(path: Path) -> tuple[list[tuple[float, float, int]], float]:
    midi = MidiFile(path.as_posix())
    ticks_per_beat = max(1, int(midi.ticks_per_beat))
    tempo = 500000
    active: dict[tuple[int, int], list[tuple[float, int]]] = {}
    notes: list[tuple[float, float, int]] = []
    timeline_seconds = 0.0
    for track in midi.tracks:
        track_seconds = 0.0
        local_tempo = tempo
        for msg in track:
            track_seconds += float(msg.time) * (local_tempo / 1_000_000.0) / ticks_per_beat
            if msg.type == "set_tempo":
                local_tempo = int(msg.tempo)
            if msg.type == "note_on" and int(msg.velocity) > 0:
                active.setdefault((int(msg.channel), int(msg.note)), []).append((track_seconds, int(msg.note)))
            if msg.type in {"note_off", "note_on"} and int(getattr(msg, "velocity", 0)) == 0:
                key = (int(msg.channel), int(msg.note))
                slot = active.get(key, [])
                if slot:
                    start, note = slot.pop(0)
                    if track_seconds > start:
                        notes.append((start, track_seconds, note))
        timeline_seconds = max(timeline_seconds, track_seconds)
    notes.sort(key=lambda row: row[0])
    return notes, max(timeline_seconds, max((row[1] for row in notes), default=0.0))


def _score_ratio(target: float, measured: float | None, tolerance: float) -> float:
    if measured is None:
        return 0.0
    error = abs(measured - target)
    if error <= tolerance:
        return max(0.0, 1.0 - error / max(1e-6, tolerance))
    return max(0.0, 1.0 - error / max(1e-6, tolerance * 2.5))


def _measure_ratios(notes: list[tuple[float, float, int]], total: float) -> dict[str, float]:
    if not notes or total <= 0:
        return {}
    starts = [n[0] for n in notes]
    durations = [max(0.0001, n[1] - n[0]) for n in notes]
    pitches = [n[2] for n in notes]
    section = starts[int(len(starts) * 0.7)] / max(1e-6, total)
    early = sum(1 for s in starts if s <= total * 0.5)
    late = max(1, len(starts) - early)
    phrase = early / late
    short = sum(1 for d in durations if d <= 0.35)
    long = max(1, len(durations) - short)
    rhythm = short / long
    step = 0
    leap = 0
    consonant = 0
    dissonant = 0
    for idx in range(1, len(pitches)):
        diff = abs(pitches[idx] - pitches[idx - 1])
        if diff <= 2:
            step += 1
        else:
            leap += 1
        if diff % 12 in {0, 3, 4, 5, 7, 8, 9}:
            consonant += 1
        else:
            dissonant += 1
    interval = step / max(1, leap)
    harmonic = consonant / max(1, dissonant)
    density = sum(1 for s in starts if s <= total * 0.61803398875) / max(1, sum(1 for s in starts if s > total * 0.61803398875))
    return {
        "golden_section_0_618": section,
        "3:2": phrase,
        "5:3": rhythm,
        "5:4": interval,
        "8:5": density,
        "harmonic_proxy": harmonic,
    }


def main() -> int:
    out_root = ROOT_DIR / "outputs" / "ratio_controlled_song_v1"
    spec_path = out_root / "ratio_control_spec.json"
    midi_path = out_root / "full.mid"
    report_md = ROOT_DIR / "reports" / "ratio_understanding" / "ratio_controlled_generation_eval.md"
    report_json = ROOT_DIR / "reports" / "ratio_understanding" / "ratio_controlled_generation_eval.json"
    report_md.parent.mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []
    if not spec_path.exists() or not midi_path.exists():
        warnings.append("missing_ratio_control_spec_or_generated_midi")
        payload = {
            "generated_at": datetime.now(UTC).isoformat(),
            "status": "missing_inputs",
            "ratio_compliance_score": 0.0,
            "warnings": warnings,
        }
        report_json.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        report_md.write_text("# Ratio Controlled Generation Eval\n\n- status: `missing_inputs`\n", encoding="utf-8")
        print(f"RATIO_EVAL_JSON={report_json.as_posix()}")
        print("RATIO_COMPLIANCE_SCORE=0.0")
        return 1

    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    ratio_controls = spec.get("ratio_controls", [])
    notes, total = _midi_notes(midi_path)
    measured = _measure_ratios(notes, total)
    evaluations: list[dict[str, Any]] = []
    weighted_total = 0.0
    weight_sum = 0.0
    for control in ratio_controls:
        ratio_name = str(control.get("ratio_name", ""))
        target = float(control.get("target_ratio", 0.0))
        tolerance = float(control.get("tolerance", 0.08))
        confidence = float(control.get("confidence", 0.5))
        measured_ratio = measured.get(ratio_name)
        score = _score_ratio(target, measured_ratio, tolerance)
        evaluations.append(
            {
                "ratio_name": ratio_name,
                "target_ratio": target,
                "measured_ratio": measured_ratio,
                "tolerance": tolerance,
                "confidence": confidence,
                "score": round(score, 6),
                "within_tolerance": measured_ratio is not None and abs(measured_ratio - target) <= tolerance,
            }
        )
        weighted_total += score * confidence
        weight_sum += confidence
        if measured_ratio is None:
            warnings.append(f"missing_measurement_for_{ratio_name}")

    compliance_score = weighted_total / weight_sum if weight_sum > 0 else 0.0
    if compliance_score < 0.55:
        warnings.append("low_ratio_compliance_score")

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "ok",
        "ratio_compliance_score": round(compliance_score, 6),
        "ratio_controls_evaluated": len(evaluations),
        "ratio_controls_within_tolerance": sum(1 for item in evaluations if item["within_tolerance"]),
        "measured_duration_seconds": round(total, 6),
        "note_count": len(notes),
        "evaluations": evaluations,
        "warnings": sorted(set(warnings)),
    }
    report_json.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    report_md.write_text(
        "\n".join(
            [
                "# Ratio Controlled Generation Eval",
                "",
                f"- ratio_compliance_score: `{payload['ratio_compliance_score']}`",
                f"- ratio_controls_evaluated: `{payload['ratio_controls_evaluated']}`",
                f"- ratio_controls_within_tolerance: `{payload['ratio_controls_within_tolerance']}`",
                f"- measured_duration_seconds: `{payload['measured_duration_seconds']}`",
                f"- note_count: `{payload['note_count']}`",
                "",
                "## Warnings",
                *(["- none"] if not payload["warnings"] else [f"- {item}" for item in payload["warnings"]]),
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"RATIO_EVAL_MD={report_md.as_posix()}")
    print(f"RATIO_EVAL_JSON={report_json.as_posix()}")
    print(f"RATIO_COMPLIANCE_SCORE={payload['ratio_compliance_score']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

