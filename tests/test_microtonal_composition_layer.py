from __future__ import annotations

import json
from pathlib import Path

from features.microtonal.edo import edo_step_cents
from features.microtonal.just_intonation import ratio_to_cents
from features.microtonal.microtonal_export_policy import build_microtonal_export_plan
from features.microtonal.microtonal_pitch import midi_note_to_frequency
from features.microtonal.scala_scl import parse_scl_text
from scripts import export_microtonal_midi_plan, plan_microtonal_composition, regenerate_ballad_from_review


def test_review_regeneration_preserves_kept_stems(tmp_path: Path) -> None:
    source = tmp_path / "v1"
    target = tmp_path / "v2"
    for idx, (_, filename) in enumerate(regenerate_ballad_from_review.TRACK_FILES.items()):
        regenerate_ballad_from_review._write_simple_midi(source / filename, note=48 + idx, channel=idx)  # noqa: SLF001
    feedback = tmp_path / "feedback.json"
    feedback.write_text(
        json.dumps(
            {
                "keep_drums": True, "regenerate_drums": False,
                "keep_bass": False, "regenerate_bass": True,
                "keep_chords": True, "regenerate_chords": False,
                "keep_lead": False, "regenerate_lead": True,
                "keep_texture": True, "regenerate_texture": False,
                "human_rating": 8, "notes": "test", "target_changes": ["bass", "lead"],
                "mood_adjustment": "neutral", "density_adjustment": "neutral",
                "melody_adjustment": "lead movement", "harmony_adjustment": "none", "microtonal_request": "none",
            }
        ),
        encoding="utf-8",
    )
    report = regenerate_ballad_from_review.regenerate_from_review(feedback_path=feedback, source_output=source, target_output=target)
    assert "drums" in report["kept_stems"]
    assert "bass" in report["regenerated_stems"]


def test_core_microtonal_calculations() -> None:
    assert edo_step_cents(24) == 50.0
    assert abs(edo_step_cents(31) - 38.70967741935484) < 1e-9
    assert abs(ratio_to_cents("3/2") - 701.9550008653874) < 1e-9
    assert midi_note_to_frequency(69) == 440.0


def test_scala_parser_and_invalid_file() -> None:
    parsed = parse_scl_text("! x\nScale\n3\n100.0\n3/2\n700.0\n")
    assert parsed.valid is True
    assert parse_scl_text("invalid").valid is False


def test_export_policy_polyphonic_pitch_bend_rule() -> None:
    standard = build_microtonal_export_plan(strategy="standard_midi_pitch_bend", polyphonic=True)
    mpe = build_microtonal_export_plan(strategy="mpe_midi", polyphonic=True)
    assert standard["requires_channel_split_or_mpe"] is True
    assert mpe["requires_channel_split_or_mpe"] is False


def test_no_audio_cloud_training_or_private_paths() -> None:
    composition = plan_microtonal_composition.build_plan()
    export_plan = export_microtonal_midi_plan.build_export_plan()
    assert composition["constraints"]["no_audio_generated"] is True
    assert composition["constraints"]["cloud_called"] is False
    assert composition["constraints"]["training_performed"] is False
    assert export_plan["constraints"]["no_audio_generated"] is True
    assert export_plan["constraints"]["cloud_called"] is False
    assert export_plan["constraints"]["training_performed"] is False
    text = json.dumps(composition) + json.dumps(export_plan)
    assert ("C:/" + "Users/izzyo") not in text
    assert ("C:\\" + "Users\\izzyo") not in text
