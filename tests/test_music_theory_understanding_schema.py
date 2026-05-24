from __future__ import annotations

from features.music_theory_understanding.theory_schema import FrameworkApplicability, GenerationHooks, MusicTheoryUnderstandingRecord
from features.music_theory_understanding.theory_schema import (
    FormUnderstanding,
    HarmonyUnderstanding,
    MotifUnderstanding,
    RhythmGrooveUnderstanding,
    TextureRoleUnderstanding,
    VoiceLeadingUnderstanding,
)


def test_schema_clamps_and_redacts() -> None:
    record = MusicTheoryUnderstandingRecord(
        item_id="x",
        source_artifact="a",
        source_path_redacted="C:/Users/test/private.mid",
        authorization_status="accepted",
        training_allowed=False,
        retrieval_allowed=True,
        transcription_reliability_score=1.2,
        generation_usefulness_score=-1.0,
        harmonic_interest_score=0.4,
        chord_movement_score=0.4,
        voice_leading_score=0.4,
        motif_reusability_score=0.4,
        rhythm_identity_score=0.4,
        groove_value_score=0.4,
        form_development_score=0.4,
        texture_value_score=0.4,
        clutter_penalty=0.1,
        random_note_penalty=0.2,
        harmony_understanding=HarmonyUnderstanding(False, None, None, [], False, False, 0.3, []),
        voice_leading_understanding=VoiceLeadingUnderstanding(False, 0.4, 0.6, 0.2, 0.5, 0.4, []),
        motif_understanding=MotifUnderstanding(False, True, 0.4, 0.5, 0.3, []),
        rhythm_understanding=RhythmGrooveUnderstanding(False, 0.4, 0.3, 0.5, 0.6, 0.4, []),
        form_understanding=FormUnderstanding(False, 3, 0.3, 0.5, 0.4, 0.4, []),
        texture_role_understanding=TextureRoleUnderstanding(False, 0.4, 0.5, 0.5, 0.4, 0.4, []),
        generation_hooks=GenerationHooks(
            target_tempo_range=[120, 80],
            target_key_or_mode="ambiguous",
            chord_movement_strategy="modal",
            bass_motion_strategy="step",
            voice_leading_strategy="step",
            motif_development_strategy="repeat",
            rhythm_strategy="groove",
            form_strategy="hybrid",
            texture_strategy="minimal",
            confidence=2.0,
        ),
    )
    assert record.transcription_reliability_score == 1.0
    assert record.generation_usefulness_score == 0.0
    assert "<PRIVATE_LOCAL_PATH>" in record.source_path_redacted


def test_framework_applicability_not_applicable_unsets_applicable() -> None:
    f = FrameworkApplicability("x", applicable=True, not_applicable=True, confidence=1.2, reasons=[])
    assert f.applicable is False
    assert f.not_applicable is True
    assert f.confidence == 1.0
