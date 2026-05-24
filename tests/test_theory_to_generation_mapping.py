from __future__ import annotations

from features.music_theory_understanding import build_theory_record
from features.music_theory_understanding.theory_to_generation import map_theory_to_generation_hooks


def test_mapping_contains_required_generation_fields() -> None:
    record = build_theory_record(
        {
            "item_id": "x",
            "source_artifact": "a",
            "source_path_redacted": "a.mid",
            "authorization_status": "accepted",
            "training_allowed": False,
            "retrieval_allowed": True,
            "harmony_quality": 7,
            "melody_quality": 7,
            "rhythm_quality": 7,
            "texture_quality": 6,
            "arrangement_quality": 6,
            "musicality_quality": 7,
            "weirdness_quality": 5,
            "tags": [],
        }
    )
    hooks = map_theory_to_generation_hooks(record)
    assert len(hooks.target_tempo_range) == 2
    assert isinstance(hooks.chord_movement_strategy, str)
    assert isinstance(hooks.tension_curve, list)
    assert isinstance(hooks.source_records_used, list)
