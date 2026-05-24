from __future__ import annotations

from dataclasses import dataclass

from .source_understanding_schema import SourceUnderstandingRecord, clamp01


@dataclass(frozen=True)
class GenerationControlMap:
    tempo_range: list[int]
    rhythmic_density: float
    harmonic_complexity: float
    motif_repetition: float
    arrangement_energy_curve: list[float]
    preserve_tags: list[str]
    avoid_tags: list[str]
    confidence: float
    source_record_ids: list[str]


def _curve(anchor: float) -> list[float]:
    return [clamp01(anchor * mult) for mult in (0.7, 0.9, 1.0, 0.85, 0.75)]


def map_source_to_generation(record: SourceUnderstandingRecord) -> GenerationControlMap:
    controls = record.generation_controls
    base_density = float(controls.get("density", 0.45))
    base_complexity = float(controls.get("complexity", 0.4))
    base_repetition = float(controls.get("motif_repetition", 0.5))
    if "high_energy" in record.generation_tags:
        base_density += 0.2
    if "harmonic_rich" in record.generation_tags:
        base_complexity += 0.2
    if "minimal" in record.generation_tags:
        base_density -= 0.2
    tempo_center = int(controls.get("tempo_hint_bpm", 100))
    low = max(50, tempo_center - 12)
    high = min(190, tempo_center + 14)
    preserve = [tag for tag in record.generation_tags if tag in {"groove_lock", "harmonic_rich", "motif_hook"}]
    avoid = [tag for tag in record.generation_tags if tag in {"muddy_low_end", "overbusy"}]
    return GenerationControlMap(
        tempo_range=[low, high],
        rhythmic_density=clamp01(base_density),
        harmonic_complexity=clamp01(base_complexity),
        motif_repetition=clamp01(base_repetition),
        arrangement_energy_curve=_curve(clamp01(record.confidence)),
        preserve_tags=preserve,
        avoid_tags=avoid,
        confidence=clamp01(record.confidence),
        source_record_ids=[record.record_id],
    )
