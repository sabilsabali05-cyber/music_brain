from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TypedDict


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MicroTimingRecord(TypedDict):
    record_id: str
    start_seconds: float
    end_seconds: float
    local_tempo_bpm: float
    pulse_stability: float
    microtiming_bias_ms: float
    microtiming_jitter_ms: float
    microtiming_summary: str
    confidence: float
    ambiguity: float
    limitations: list[str]


class SubdivisionGridRecord(TypedDict):
    record_id: str
    start_seconds: float
    end_seconds: float
    local_tempo_bpm: float
    subdivision_type: str
    grid_confidence: float
    ambiguity: float
    straightness: float
    tripletness: float
    swingness: float
    randomness: float
    limitations: list[str]


class BeatMeterHypothesis(TypedDict):
    hypothesis_id: str
    meter: str
    beats_per_bar: int
    beat_unit: int
    confidence: float
    ambiguity: float
    evidence: dict[str, Any]
    limitations: list[str]


class CyclePatternRecord(TypedDict):
    cycle_id: str
    start_seconds: float
    end_seconds: float
    cycle_length_beats: float
    confidence: float
    ambiguity: float
    supporting_subdivision: str
    evidence: dict[str, Any]
    limitations: list[str]


class PhraseRhythmRecord(TypedDict):
    phrase_id: str
    start_seconds: float
    end_seconds: float
    phrase_span_beats: float
    phrase_shape: str
    pulse_stability: float
    confidence: float
    ambiguity: float
    evidence: dict[str, Any]
    limitations: list[str]


class MacroTimeRecord(TypedDict):
    macro_id: str
    start_seconds: float
    end_seconds: float
    macro_section_candidate: str
    local_tempo_bpm: float
    pulse_stability: float
    confidence: float
    ambiguity: float
    evidence: dict[str, Any]
    limitations: list[str]


def base_payload(
    *,
    performance_id: str,
    source_name: str,
    segment_run_id: str,
    source_artifact_paths: dict[str, str | None],
    confidence: float,
    ambiguity: float,
    limitations: list[str],
    summary: dict[str, Any],
    microtiming_records: list[MicroTimingRecord],
    subdivision_grid_records: list[SubdivisionGridRecord],
    beat_meter_hypotheses: list[BeatMeterHypothesis],
    cycle_pattern_records: list[CyclePatternRecord],
    phrase_rhythm_records: list[PhraseRhythmRecord],
    macro_time_records: list[MacroTimeRecord],
) -> dict[str, Any]:
    return {
        "performance_id": performance_id,
        "source_name": source_name,
        "segment_run_id": segment_run_id,
        "source_artifact_paths": source_artifact_paths,
        "feature_version": "meter_time_v1",
        "extractor_name": "meter_time_extractor_v1",
        "confidence": round(float(confidence), 6),
        "ambiguity": round(float(ambiguity), 6),
        "limitations": [str(item) for item in limitations],
        "summary": summary,
        "microtiming_records": microtiming_records,
        "subdivision_grid_records": subdivision_grid_records,
        "beat_meter_hypotheses": beat_meter_hypotheses,
        "cycle_pattern_records": cycle_pattern_records,
        "phrase_rhythm_records": phrase_rhythm_records,
        "macro_time_records": macro_time_records,
        "generated_at": _now_iso(),
    }
