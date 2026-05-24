from __future__ import annotations

from features.source_understanding.source_to_generation import map_source_to_generation
from features.source_understanding.source_understanding_schema import build_source_understanding_record


def test_source_to_generation_mapping_outputs_controls() -> None:
    record = build_source_understanding_record(
        record_id="r1",
        item_id="i1",
        source_artifact="demo.mid",
        source_path_redacted="demo.mid",
        source_type="symbolic",
        authorization_status="authorized",
        training_allowed=False,
        retrieval_allowed=True,
        raw_audio_processing_allowed=False,
        evidence_types=["normalized_corpus_row"],
        evidence_summary="demo",
        confidence=0.83,
        confidence_reason="high confidence",
        generation_tags=["high_energy", "harmonic_rich", "groove_lock"],
        generation_controls={"tempo_hint_bpm": 118, "density": 0.6, "complexity": 0.7, "motif_repetition": 0.55},
    )
    mapped = map_source_to_generation(record)
    assert len(mapped.tempo_range) == 2
    assert mapped.rhythmic_density > 0.6
    assert mapped.harmonic_complexity > 0.7
    assert "groove_lock" in mapped.preserve_tags
