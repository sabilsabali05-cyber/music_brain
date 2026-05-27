from __future__ import annotations

import hashlib

import pytest

from features.taste_database.feedback import create_feedback_record
from features.taste_database.retrieval_memory import RetrievalMemoryPolicy
from features.taste_database.schema import ModelDerivedRef, TasteItemRecord, validate_taste_item_record


def test_taste_records_exclude_private_paths() -> None:
    record = TasteItemRecord(
        taste_item_id="taste_001",
        loop_id="loop_001",
        source_id_hash=hashlib.sha256(b"loop_001").hexdigest(),
        source_redacted_path="D:/private/library/loop.wav",
        model_witness_refs=[
            ModelDerivedRef(
                witness_id="basicpitch",
                witness_tool="basicpitch",
                witness_role="witness",
                derived_output_ref_hash=hashlib.sha256(b"bp-output").hexdigest(),
            )
        ],
        retrieval_tags=["groove"],
    )
    payload = record.to_dict()
    assert "D:/private" not in payload["source_redacted_path"]
    assert "<PRIVATE_LOCAL_PATH>" in payload["source_redacted_path"]


def test_raw_audio_paths_are_redacted_local_only() -> None:
    ok, reason = validate_taste_item_record(
        {
            "loop_id": "loop_002",
            "source_redacted_path": "<PRIVATE_LOCAL_PATH>/library/loop_002.wav",
            "training_allowed": False,
            "model_witness_refs": [{"witness_id": "demucs"}],
        }
    )
    assert ok is True
    assert reason == "ok"


def test_feedback_records_attach_to_loop_ids() -> None:
    with pytest.raises(ValueError):
        create_feedback_record(
            feedback_id="fb_bad",
            loop_id="",
            taste_item_id="taste_001",
            decision_label="keep",
            focus_category="groove",
            sentiment="positive",
            reviewer="alice",
        )
    record = create_feedback_record(
        feedback_id="fb_ok",
        loop_id="loop_abc",
        taste_item_id="taste_abc",
        decision_label="promote",
        focus_category="harmony",
        sentiment="positive",
        reviewer="alice",
    )
    assert record.loop_id == "loop_abc"


def test_taste_item_references_model_outputs_without_committing_outputs() -> None:
    with pytest.raises(ValueError):
        ModelDerivedRef(
            witness_id="musicbert",
            witness_tool="musicbert",
            witness_role="tool",
            derived_output_ref_hash=hashlib.sha256(b"musicbert-output").hexdigest(),
            output_committed_inline=True,
        )
    ref = ModelDerivedRef(
        witness_id="demucs",
        witness_tool="demucs",
        witness_role="witness",
        derived_output_ref_hash=hashlib.sha256(b"stem-refs").hexdigest(),
        output_committed_inline=False,
    )
    assert ref.output_committed_inline is False


def test_training_allowed_defaults_false() -> None:
    policy = RetrievalMemoryPolicy()
    assert policy.training_allowed is False
    record = TasteItemRecord(
        taste_item_id="taste_003",
        loop_id="loop_003",
        source_id_hash=hashlib.sha256(b"loop_003").hexdigest(),
        source_redacted_path="E:/private/loop.wav",
        model_witness_refs=[
            ModelDerivedRef(
                witness_id="basicpitch",
                witness_tool="basicpitch",
                witness_role="witness",
                derived_output_ref_hash=hashlib.sha256(b"bp-output-2").hexdigest(),
            )
        ],
    )
    assert record.training_allowed is False
