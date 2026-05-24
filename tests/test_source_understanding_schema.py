from __future__ import annotations

from features.source_understanding.source_understanding_schema import build_source_understanding_record


def test_source_understanding_confidence_and_policy_gates() -> None:
    record = build_source_understanding_record(
        record_id="r1",
        item_id="i1",
        source_artifact="demo.mid",
        source_path_redacted="C:/Users/demo/private.mid",
        source_type="symbolic",
        authorization_status="authorized",
        training_allowed=False,
        retrieval_allowed=True,
        raw_audio_processing_allowed=False,
        evidence_types=["normalized_corpus_row"],
        evidence_summary="demo",
        confidence=0.2,
        confidence_reason="low confidence",
    )
    assert record.blocked_by_confidence is True
    assert record.usable_as_generation_evidence is False
    assert "<PRIVATE_LOCAL_PATH>/" in record.source_path_redacted

    blocked = build_source_understanding_record(
        record_id="r2",
        item_id="i2",
        source_artifact="demo2.mid",
        source_path_redacted="demo2.mid",
        source_type="symbolic",
        authorization_status="unauthorized",
        training_allowed=False,
        retrieval_allowed=False,
        raw_audio_processing_allowed=False,
        evidence_types=["normalized_corpus_row"],
        evidence_summary="demo",
        confidence=0.9,
        confidence_reason="high confidence",
    )
    assert blocked.blocked_by_policy is True
    assert blocked.usable_as_generation_evidence is False
