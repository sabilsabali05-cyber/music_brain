from __future__ import annotations

import json
import math
import sys
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mido import MidiFile

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.ratio_understanding.ratio_schema import RatioObservation, named_ratio_catalog  # noqa: E402


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:  # noqa: BLE001
        return default


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _iter_candidate_midis() -> list[Path]:
    direct = sorted((ROOT_DIR / "outputs" / "music_understanding_loop_v1" / "candidates").glob("*.mid"))
    if direct:
        return direct
    fallback: list[Path] = []
    for root in [ROOT_DIR / "outputs", ROOT_DIR / "datasets"]:
        fallback.extend(sorted(root.rglob("*.mid")))
    return fallback[:16]


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
                key = (int(msg.channel), int(msg.note))
                active.setdefault(key, []).append((track_seconds, int(msg.note)))
            if msg.type in {"note_off", "note_on"} and int(getattr(msg, "velocity", 0)) == 0:
                key = (int(msg.channel), int(msg.note))
                bucket = active.get(key, [])
                if bucket:
                    start, note = bucket.pop(0)
                    if track_seconds > start:
                        notes.append((start, track_seconds, note))
        timeline_seconds = max(timeline_seconds, track_seconds)
    notes.sort(key=lambda row: row[0])
    total = max(timeline_seconds, max((n[1] for n in notes), default=0.0))
    return notes, total


def _nearest_named_ratio(value: float) -> tuple[str, float, float]:
    catalog = named_ratio_catalog()
    best_name = "1:1"
    best_target = 1.0
    best_error = float("inf")
    for name, ratio in catalog.items():
        error = abs(value - ratio.decimal_value)
        if error < best_error:
            best_name = name
            best_target = ratio.decimal_value
            best_error = error
    return best_name, best_target, best_error


def _build_observation(
    *,
    observation_id: str,
    source_artifact: str,
    source_item_id: str,
    domain: str,
    numerator: float | None,
    denominator: float | None,
    evidence_excerpt: str,
    confidence: float,
    status: str = "observed",
    notes: list[str] | None = None,
) -> RatioObservation:
    if numerator is None or denominator is None or denominator <= 0:
        return RatioObservation(
            observation_id=observation_id,
            source_artifact=source_artifact,
            source_item_id=source_item_id,
            domain=domain,
            ratio_name="unknown",
            observed_numerator=numerator,
            observed_denominator=denominator,
            observed_ratio=None,
            target_ratio=None,
            absolute_error=None,
            within_tolerance=False,
            confidence=confidence,
            evidence_kind="symbolic_features",
            evidence_excerpt=evidence_excerpt,
            status=status,
            notes=list(notes or []),
        )
    observed_ratio = float(numerator) / float(denominator)
    ratio_name, target, error = _nearest_named_ratio(observed_ratio)
    tolerance = named_ratio_catalog()[ratio_name].tolerance
    return RatioObservation(
        observation_id=observation_id,
        source_artifact=source_artifact,
        source_item_id=source_item_id,
        domain=domain,
        ratio_name=ratio_name,
        observed_numerator=float(numerator),
        observed_denominator=float(denominator),
        observed_ratio=observed_ratio,
        target_ratio=target,
        absolute_error=error,
        within_tolerance=error <= tolerance,
        confidence=confidence,
        evidence_kind="symbolic_features",
        evidence_excerpt=evidence_excerpt,
        status=status,
        notes=list(notes or []),
    )


def _analyze_midi(path: Path) -> list[RatioObservation]:
    notes, total = _midi_notes(path)
    source_item_id = path.stem
    if not notes or total <= 0:
        return [
            _build_observation(
                observation_id=f"{source_item_id}_section",
                source_artifact=path.as_posix(),
                source_item_id=source_item_id,
                domain="section",
                numerator=None,
                denominator=None,
                evidence_excerpt="No usable note/timeline evidence.",
                confidence=0.0,
                status="unavailable",
                notes=["missing_or_empty_symbolic_notes"],
            )
        ]

    durations = [max(0.0001, end - start) for start, end, _ in notes]
    pitches = [pitch for _, _, pitch in notes]
    starts = [start for start, _, _ in notes]
    midpoint = total * 0.5
    early_count = sum(1 for start in starts if start <= midpoint)
    late_count = max(1, len(starts) - early_count)
    section_peak = starts[int(len(starts) * 0.7)] if len(starts) > 1 else starts[0]

    short_count = sum(1 for d in durations if d <= 0.35)
    long_count = max(1, len(durations) - short_count)

    step_count = 0
    leap_count = 0
    for idx in range(1, len(pitches)):
        diff = abs(pitches[idx] - pitches[idx - 1])
        if diff <= 2:
            step_count += 1
        else:
            leap_count += 1
    leap_count = max(1, leap_count)

    consonant = 0
    dissonant = 0
    for idx in range(1, len(pitches)):
        interval = abs(pitches[idx] - pitches[idx - 1]) % 12
        if interval in {0, 3, 4, 5, 7, 8, 9}:
            consonant += 1
        else:
            dissonant += 1
    dissonant = max(1, dissonant)

    motif_cells = Counter()
    for idx in range(2, len(pitches)):
        motif_cells[(pitches[idx - 2], pitches[idx - 1], pitches[idx])] += 1
    repeated = sum(1 for c in motif_cells.values() if c >= 2)
    unique = max(1, len(motif_cells) - repeated)

    observations = [
        _build_observation(
            observation_id=f"{source_item_id}_section",
            source_artifact=path.as_posix(),
            source_item_id=source_item_id,
            domain="section",
            numerator=section_peak,
            denominator=total,
            evidence_excerpt="Section anchor from dense onset position over full duration.",
            confidence=min(1.0, 0.35 + len(notes) / 240.0),
        ),
        _build_observation(
            observation_id=f"{source_item_id}_phrase",
            source_artifact=path.as_posix(),
            source_item_id=source_item_id,
            domain="phrase",
            numerator=early_count,
            denominator=late_count,
            evidence_excerpt="Phrase ratio from early/late event distribution.",
            confidence=min(1.0, 0.3 + len(notes) / 220.0),
        ),
        _build_observation(
            observation_id=f"{source_item_id}_rhythm",
            source_artifact=path.as_posix(),
            source_item_id=source_item_id,
            domain="rhythm",
            numerator=short_count,
            denominator=long_count,
            evidence_excerpt="Rhythm ratio from short/long note durations.",
            confidence=min(1.0, 0.3 + len(durations) / 220.0),
        ),
        _build_observation(
            observation_id=f"{source_item_id}_harmonic",
            source_artifact=path.as_posix(),
            source_item_id=source_item_id,
            domain="harmonic",
            numerator=consonant,
            denominator=dissonant,
            evidence_excerpt="Harmonic interval balance from melodic interval classes.",
            confidence=min(1.0, 0.25 + len(pitches) / 260.0),
        ),
        _build_observation(
            observation_id=f"{source_item_id}_motif",
            source_artifact=path.as_posix(),
            source_item_id=source_item_id,
            domain="motif",
            numerator=repeated,
            denominator=unique,
            evidence_excerpt="Motif recurrence ratio from repeated 3-note cells.",
            confidence=min(1.0, 0.2 + len(motif_cells) / 180.0),
        ),
        _build_observation(
            observation_id=f"{source_item_id}_interval",
            source_artifact=path.as_posix(),
            source_item_id=source_item_id,
            domain="interval",
            numerator=step_count,
            denominator=leap_count,
            evidence_excerpt="Interval motion ratio from stepwise/leap transitions.",
            confidence=min(1.0, 0.25 + len(pitches) / 260.0),
        ),
        _build_observation(
            observation_id=f"{source_item_id}_density",
            source_artifact=path.as_posix(),
            source_item_id=source_item_id,
            domain="density",
            numerator=sum(1 for start in starts if start <= total * 0.61803398875),
            denominator=max(1, sum(1 for start in starts if start > total * 0.61803398875)),
            evidence_excerpt="Density split across golden-section boundary.",
            confidence=min(1.0, 0.3 + len(starts) / 240.0),
        ),
    ]
    return observations


def main() -> int:
    output_jsonl = ROOT_DIR / "datasets" / "ratio_understanding" / "ratio_observations.jsonl"
    report_md = ROOT_DIR / "reports" / "ratio_understanding" / "ratio_understanding_report.md"
    report_json = ROOT_DIR / "reports" / "ratio_understanding" / "ratio_understanding_report.json"
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    report_md.parent.mkdir(parents=True, exist_ok=True)

    evidence_sources = [
        ROOT_DIR / "datasets" / "source_understanding" / "source_understanding_records.jsonl",
        ROOT_DIR / "datasets" / "music_theory" / "theory_understanding_records.jsonl",
        ROOT_DIR / "reports" / "source_understanding" / "source_understanding_report.json",
        ROOT_DIR / "reports" / "taste_learning" / "ranked_midi_candidates_report.json",
        ROOT_DIR / "outputs" / "music_understanding_loop_v1",
        ROOT_DIR / "outputs" / "beat_battle_site",
    ]

    observations: list[RatioObservation] = []
    midi_paths = _iter_candidate_midis()
    if midi_paths:
        for midi_path in midi_paths[:8]:
            observations.extend(_analyze_midi(midi_path))
    else:
        for domain in ["section", "phrase", "rhythm", "harmonic", "motif"]:
            observations.append(
                _build_observation(
                    observation_id=f"missing_{domain}",
                    source_artifact="none",
                    source_item_id="none",
                    domain=domain,
                    numerator=None,
                    denominator=None,
                    evidence_excerpt="No symbolic MIDI artifacts found for ratio extraction.",
                    confidence=0.0,
                    status="unavailable",
                    notes=["no_symbolic_artifacts_available"],
                )
            )

    output_jsonl.write_text(
        "\n".join(json.dumps(item.to_dict(), ensure_ascii=True) for item in observations) + "\n",
        encoding="utf-8",
    )

    high_confidence = [o for o in observations if o.status == "observed" and o.confidence >= 0.75]
    golden_hits = [
        o
        for o in observations
        if o.status == "observed" and o.ratio_name in {"golden_ratio_phi", "golden_section_0_618", "inverse_phi_0_382"}
    ]
    unavailable = [o for o in observations if o.status == "unavailable"]
    unknown = [o for o in observations if o.status == "unknown"]
    by_domain = Counter(o.domain for o in observations)
    by_ratio_name = Counter(o.ratio_name for o in observations if o.status == "observed")
    source_report = _load_json(ROOT_DIR / "reports" / "source_understanding" / "source_understanding_report.json")

    report_payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "analysis_type": "ratio_understanding",
        "evidence_based_only": True,
        "source_understanding_rows_considered": int(source_report.get("rows_considered", 0)),
        "ratio_observations_count": len(observations),
        "high_confidence_observations_count": len(high_confidence),
        "golden_section_findings_count": len(golden_hits),
        "unavailable_count": len(unavailable),
        "unknown_count": len(unknown),
        "midi_artifacts_analyzed_count": len(midi_paths[:8]),
        "domains_covered": sorted(by_domain.keys()),
        "observations_by_domain": dict(by_domain),
        "observations_by_ratio_name": dict(by_ratio_name),
        "evidence_sources": [{"path": path.as_posix(), "available": path.exists()} for path in evidence_sources],
        "notes": [
            "Analysis uses only local symbolic/features artifacts where available.",
            "Unavailable/unknown statuses are preserved without fabricated evidence.",
            "No universal golden-ratio forcing was applied.",
        ],
    }
    report_json.write_text(json.dumps(report_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    report_md.write_text(
        "\n".join(
            [
                "# Ratio Understanding Report",
                "",
                f"- ratio_observations_count: `{report_payload['ratio_observations_count']}`",
                f"- high_confidence_observations_count: `{report_payload['high_confidence_observations_count']}`",
                f"- golden_section_findings_count: `{report_payload['golden_section_findings_count']}`",
                f"- unavailable_count: `{report_payload['unavailable_count']}`",
                f"- unknown_count: `{report_payload['unknown_count']}`",
                f"- midi_artifacts_analyzed_count: `{report_payload['midi_artifacts_analyzed_count']}`",
                f"- domains_covered: `{report_payload['domains_covered']}`",
                "",
                "## Evidence Sources",
                *[
                    f"- `{item['path']}` -> `{'available' if item['available'] else 'missing'}`"
                    for item in report_payload["evidence_sources"]
                ],
                "",
                "## Notes",
                *[f"- {item}" for item in report_payload["notes"]],
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"RATIO_OBSERVATIONS_JSONL={output_jsonl.as_posix()}")
    print(f"RATIO_REPORT_MD={report_md.as_posix()}")
    print(f"RATIO_REPORT_JSON={report_json.as_posix()}")
    print(f"RATIO_OBSERVATIONS_COUNT={report_payload['ratio_observations_count']}")
    print(f"HIGH_CONFIDENCE_OBSERVATIONS_COUNT={report_payload['high_confidence_observations_count']}")
    print(f"GOLDEN_SECTION_FINDINGS_COUNT={report_payload['golden_section_findings_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

