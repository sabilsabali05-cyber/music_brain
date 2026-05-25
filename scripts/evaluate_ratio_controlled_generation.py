from __future__ import annotations

import json
import math
import os
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


def _measure_ratios(notes: list[tuple[float, float, int]], total: float, plan: dict[str, Any] | None) -> dict[str, Any]:
    if not notes or total <= 0:
        return {}
    starts = sorted(n[0] for n in notes)
    durations = [max(0.0001, n[1] - n[0]) for n in notes]
    pitches = [n[2] for n in sorted(notes, key=lambda x: x[0])]
    pg = (plan or {}).get("pre_generation_plan", {})
    phrase_boundaries = [float(x) for x in pg.get("phrase_grid", {}).get("phrase_boundaries_seconds", []) if float(x) <= total + 1e-6]
    if len(phrase_boundaries) < 3:
        phrase_boundaries = [0.0, total * 0.55, total]
    phrase_lengths = [max(0.001, phrase_boundaries[i + 1] - phrase_boundaries[i]) for i in range(len(phrase_boundaries) - 1)]
    long_phrase = max(phrase_lengths)
    short_phrase = min(phrase_lengths)
    phrase_ratio = long_phrase / max(0.001, short_phrase)
    chord_starts = sorted({round(s, 3) for s, _, p in notes if p <= 60})
    if len(chord_starts) < 4:
        chord_starts = phrase_boundaries[:-1]
    chord_intervals = [max(0.001, chord_starts[i + 1] - chord_starts[i]) for i in range(len(chord_starts) - 1)]
    chord_long = max(chord_intervals) if chord_intervals else 0.0
    chord_short = min(chord_intervals) if chord_intervals else 0.0
    chord_ratio = chord_long / max(0.001, chord_short) if chord_intervals else None
    onset_times = sorted({round(s, 3) for s, _, _ in notes})
    onset_deltas = [max(0.001, onset_times[i + 1] - onset_times[i]) for i in range(len(onset_times) - 1)]
    long_threshold = sum(onset_deltas) / max(1, len(onset_deltas)) if onset_deltas else 0.0
    long_cells = [d for d in onset_deltas if d >= long_threshold]
    short_cells = [d for d in onset_deltas if d < long_threshold]
    rhythm_ratio = (sum(long_cells) / max(1, len(long_cells))) / max(
        0.001, (sum(short_cells) / max(1, len(short_cells)))
    )
    step = 0
    leap = 0
    for idx in range(1, len(pitches)):
        diff = abs(pitches[idx] - pitches[idx - 1])
        if diff <= 2:
            step += 1
        else:
            leap += 1
    interval = step / max(1, leap)
    window = 4.0
    buckets: list[tuple[float, int]] = []
    t = 0.0
    while t < total:
        count = sum(1 for s in onset_times if t <= s < min(total, t + window))
        buckets.append((t, count))
        t += window / 2.0
    peak_t, peak_count = max(buckets, key=lambda row: row[1]) if buckets else (0.0, 0)
    pre_peak = sum(c for x, c in buckets if x <= peak_t and x < total * 0.61803398875)
    post_peak = sum(c for x, c in buckets if x >= peak_t and x >= total * 0.61803398875)
    density = pre_peak / max(1, post_peak)
    return {
        "golden_section_0_618": peak_t / max(1e-6, total),
        "3:2": phrase_ratio,
        "5:3": rhythm_ratio,
        "5:4": interval,
        "8:5": density,
        "density_peak_time_seconds": peak_t,
        "density_peak_count": peak_count,
        "phrase_boundaries_seconds": phrase_boundaries,
        "chord_boundary_ratio": chord_ratio,
    }


def main() -> int:
    out_dir_name = os.environ.get("RATIO_OUTPUT_DIR", "ratio_controlled_song_v2")
    report_prefix = os.environ.get("RATIO_EVAL_PREFIX", "ratio_controlled_generation_v2_eval")
    out_root = ROOT_DIR / "outputs" / out_dir_name
    spec_path = out_root / "ratio_control_spec.json"
    plan_path = out_root / "ratio_plan.json"
    midi_path = out_root / "full.mid"
    report_md = ROOT_DIR / "reports" / "ratio_understanding" / f"{report_prefix}.md"
    report_json = ROOT_DIR / "reports" / "ratio_understanding" / f"{report_prefix}.json"
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
    plan = None
    if plan_path.exists():
        try:
            loaded_plan = json.loads(plan_path.read_text(encoding="utf-8"))
            if isinstance(loaded_plan, dict):
                plan = loaded_plan
        except json.JSONDecodeError:
            warnings.append("invalid_ratio_plan_json")
    else:
        warnings.append("ratio_plan_missing")
    ratio_controls = spec.get("ratio_controls", [])
    notes, total = _midi_notes(midi_path)
    measured = _measure_ratios(notes, total, plan)
    evaluations: list[dict[str, Any]] = []
    weighted_total = 0.0
    weight_sum = 0.0
    control_scores: dict[str, float] = {}
    for control in ratio_controls:
        ratio_name = str(control.get("ratio_name", ""))
        target = float(control.get("target_ratio", 0.0))
        if plan and ratio_name in plan.get("controls", {}):
            target = float(plan["controls"][ratio_name].get("target", target))
        tolerance = float(control.get("tolerance", 0.08))
        confidence = float(control.get("confidence", 0.5))
        measured_ratio = measured.get(ratio_name)
        score = _score_ratio(target, measured_ratio, tolerance)
        error = abs(float(measured_ratio) - target) if measured_ratio is not None else None
        evaluations.append(
            {
                "ratio_name": ratio_name,
                "target_ratio": target,
                "measured_ratio": measured_ratio,
                "absolute_error": error,
                "tolerance": tolerance,
                "confidence": confidence,
                "score": round(score, 6),
                "within_tolerance": measured_ratio is not None and abs(measured_ratio - target) <= tolerance,
            }
        )
        control_scores[ratio_name] = round(score, 6)
        weighted_total += score * confidence
        weight_sum += confidence
        if measured_ratio is None:
            warnings.append(f"missing_measurement_for_{ratio_name}")

    compliance_score = weighted_total / weight_sum if weight_sum > 0 else 0.0
    random_note_penalty = 0.0
    if len(notes) > 1600:
        random_note_penalty = min(0.15, (len(notes) - 1600) / 8000.0)
        warnings.append("high_note_count_randomness_risk")
    too_rigid_penalty = 0.0
    if plan:
        phrase_count = len(measured.get("phrase_boundaries_seconds", []))
        if phrase_count > 44:
            too_rigid_penalty = min(0.18, (phrase_count - 44) / 150.0)
            warnings.append("too_rigid_phrase_grid")
    compliance_score = max(0.0, compliance_score - random_note_penalty - too_rigid_penalty)
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
        "random_note_penalty": round(random_note_penalty, 6),
        "too_rigid_penalty": round(too_rigid_penalty, 6),
        "density_peak_time_seconds": round(float(measured.get("density_peak_time_seconds", 0.0)), 6),
        "density_peak_ratio_measured": measured.get("8:5"),
        "phrase_boundary_ratio_measured": measured.get("3:2"),
        "chord_boundary_ratio_measured": measured.get("chord_boundary_ratio"),
        "rhythm_onset_ratio_measured": measured.get("5:3"),
        "interval_ratio_measured": measured.get("5:4"),
        "per_control_scores": control_scores,
        "plan_used": f"outputs/{out_dir_name}/ratio_plan.json" if plan else None,
        "evaluations": evaluations,
        "warnings": sorted(set(warnings)),
    }
    report_json.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    report_md.write_text(
        "\n".join(
            [
                "# Ratio Controlled Generation Eval (v2)",
                "",
                f"- ratio_compliance_score: `{payload['ratio_compliance_score']}`",
                f"- ratio_controls_evaluated: `{payload['ratio_controls_evaluated']}`",
                f"- ratio_controls_within_tolerance: `{payload['ratio_controls_within_tolerance']}`",
                f"- measured_duration_seconds: `{payload['measured_duration_seconds']}`",
                f"- note_count: `{payload['note_count']}`",
                f"- random_note_penalty: `{payload['random_note_penalty']}`",
                f"- too_rigid_penalty: `{payload['too_rigid_penalty']}`",
                f"- golden_peak_ratio_measured: `{measured.get('golden_section_0_618')}`",
                f"- phrase_ratio_measured: `{payload['phrase_boundary_ratio_measured']}`",
                f"- rhythm_ratio_measured: `{payload['rhythm_onset_ratio_measured']}`",
                f"- density_ratio_measured: `{payload['density_peak_ratio_measured']}`",
                f"- interval_ratio_measured: `{payload['interval_ratio_measured']}`",
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

