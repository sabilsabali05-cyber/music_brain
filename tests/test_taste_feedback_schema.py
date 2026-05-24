from __future__ import annotations

from features.taste_learning.taste_feedback_schema import validate_taste_feedback


def test_taste_feedback_schema_blocks_unauthorized() -> None:
    ok, reason = validate_taste_feedback(
        {
            "taste_label": "like",
            "authorization_status": "restricted",
            "source_authorized_for_learning": True,
        }
    )
    assert ok is False
    assert reason == "unauthorized_feedback_source"


def test_taste_feedback_schema_accepts_valid_row() -> None:
    ok, reason = validate_taste_feedback(
        {
            "taste_label": "love",
            "authorization_status": "authorized",
            "source_authorized_for_learning": True,
        }
    )
    assert ok is True
    assert reason == "ok"
