from __future__ import annotations

from .form_analysis import analyze_form
from .harmony_analysis import analyze_harmony
from .motif_analysis import analyze_motif
from .rhythm_analysis import analyze_rhythm
from .texture_role_analysis import analyze_texture_roles
from .theory_confidence import confidence_gate_blocked, reliability_from_row
from .theory_schema import GenerationHooks, MusicTheoryUnderstandingRecord, clamp01
from .theory_to_generation import map_theory_to_generation_hooks
from .voice_leading_analysis import analyze_voice_leading


def build_theory_record(row: dict, music_intelligence_row: dict | None = None) -> MusicTheoryUnderstandingRecord:
    reliability = reliability_from_row(row, music_intelligence_row)
    harmony_understanding, harmony_scores = analyze_harmony(row, reliability)
    voice_understanding, voice_scores = analyze_voice_leading(row, reliability)
    motif_understanding, motif_scores = analyze_motif(row, reliability)
    rhythm_understanding, rhythm_scores = analyze_rhythm(row, reliability)
    form_understanding, form_scores = analyze_form(row, reliability)
    texture_understanding, texture_scores = analyze_texture_roles(row, reliability)
    clutter_penalty = clamp01(1.0 - texture_understanding.layer_separation)
    random_note_penalty = clamp01(
        0.65 * (1.0 - voice_understanding.stepwise_motion_ratio) + 0.35 * harmony_understanding.random_clash_risk
    )
    usefulness = clamp01(
        (
            harmony_scores["harmonic_interest_score"]
            + voice_scores["voice_leading_score"]
            + motif_scores["motif_reusability_score"]
            + rhythm_scores["groove_value_score"]
            + form_scores["form_development_score"]
            + texture_scores["texture_value_score"]
        )
        / 6.0
        - 0.35 * clutter_penalty
        - 0.45 * random_note_penalty
    )
    blocked_policy = str(row.get("authorization_status", "")).lower() in {"unauthorized", "private", "sensitive"}
    blocked_conf = confidence_gate_blocked(reliability)
    provisional_hooks = GenerationHooks(
        target_tempo_range=[70, 90],
        target_key_or_mode="ambiguous_mode_allowed",
        chord_movement_strategy="modal_or_pedal_without_forced_function",
        bass_motion_strategy="root_pedal_support",
        voice_leading_strategy="minimize_large_leaps",
        motif_development_strategy="short-call-response-cells",
        rhythm_strategy="sparse_grid_with_accent_lifts",
        form_strategy="hybrid_form_with_anchor_refrain",
        texture_strategy="minimal_texture_roles",
        confidence=0.1,
    )
    seed_record = MusicTheoryUnderstandingRecord(
        item_id=str(row.get("item_id", "")),
        source_artifact=str(row.get("source_artifact", "")),
        source_path_redacted=str(row.get("source_path_redacted", row.get("source_artifact", ""))),
        authorization_status=str(row.get("authorization_status", "unknown")).lower(),
        training_allowed=bool(row.get("training_allowed", False)),
        retrieval_allowed=bool(row.get("retrieval_allowed", True)),
        transcription_reliability_score=reliability,
        generation_usefulness_score=usefulness,
        harmonic_interest_score=harmony_scores["harmonic_interest_score"],
        chord_movement_score=harmony_scores["chord_movement_score"],
        voice_leading_score=voice_scores["voice_leading_score"],
        motif_reusability_score=motif_scores["motif_reusability_score"],
        rhythm_identity_score=rhythm_scores["rhythm_identity_score"],
        groove_value_score=rhythm_scores["groove_value_score"],
        form_development_score=form_scores["form_development_score"],
        texture_value_score=texture_scores["texture_value_score"],
        clutter_penalty=clutter_penalty,
        random_note_penalty=random_note_penalty,
        harmony_understanding=harmony_understanding,
        voice_leading_understanding=voice_understanding,
        motif_understanding=motif_understanding,
        rhythm_understanding=rhythm_understanding,
        form_understanding=form_understanding,
        texture_role_understanding=texture_understanding,
        generation_hooks=provisional_hooks,
        blocked_by_policy=blocked_policy,
        blocked_by_confidence=blocked_conf,
        theory_notes=[
            "No forced Western reading on ambiguous material.",
            "not_applicable used for weak evidence.",
            "No training-safe assumptions.",
        ],
    )
    hooks = map_theory_to_generation_hooks(seed_record)
    return MusicTheoryUnderstandingRecord(
        item_id=seed_record.item_id,
        source_artifact=seed_record.source_artifact,
        source_path_redacted=seed_record.source_path_redacted,
        authorization_status=seed_record.authorization_status,
        training_allowed=seed_record.training_allowed,
        retrieval_allowed=seed_record.retrieval_allowed,
        transcription_reliability_score=seed_record.transcription_reliability_score,
        generation_usefulness_score=seed_record.generation_usefulness_score,
        harmonic_interest_score=seed_record.harmonic_interest_score,
        chord_movement_score=seed_record.chord_movement_score,
        voice_leading_score=seed_record.voice_leading_score,
        motif_reusability_score=seed_record.motif_reusability_score,
        rhythm_identity_score=seed_record.rhythm_identity_score,
        groove_value_score=seed_record.groove_value_score,
        form_development_score=seed_record.form_development_score,
        texture_value_score=seed_record.texture_value_score,
        clutter_penalty=seed_record.clutter_penalty,
        random_note_penalty=seed_record.random_note_penalty,
        harmony_understanding=seed_record.harmony_understanding,
        voice_leading_understanding=seed_record.voice_leading_understanding,
        motif_understanding=seed_record.motif_understanding,
        rhythm_understanding=seed_record.rhythm_understanding,
        form_understanding=seed_record.form_understanding,
        texture_role_understanding=seed_record.texture_role_understanding,
        generation_hooks=hooks,
        blocked_by_policy=seed_record.blocked_by_policy,
        blocked_by_confidence=seed_record.blocked_by_confidence,
        theory_notes=seed_record.theory_notes,
    )


__all__ = ["MusicTheoryUnderstandingRecord", "build_theory_record"]
