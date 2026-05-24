from __future__ import annotations

from .theory_schema import GenerationHooks, MusicTheoryUnderstandingRecord, clamp01


def _curve(anchor: float) -> list[float]:
    return [clamp01(anchor * x) for x in (0.6, 0.8, 1.0, 0.85, 0.7)]


def map_theory_to_generation_hooks(record: MusicTheoryUnderstandingRecord) -> GenerationHooks:
    tempo_center = 78 + int(round(record.rhythm_identity_score * 70))
    low = max(50, tempo_center - 8)
    high = min(180, tempo_center + 12)
    if record.form_understanding.loop_tendency > 0.65:
        form_strategy = "loop_8_or_16_bar_with_variation"
    elif record.form_understanding.through_composed_tendency > 0.6:
        form_strategy = "through_composed_sections_with_motif_recall"
    else:
        form_strategy = "hybrid_form_with_anchor_refrain"
    if record.harmony_understanding.not_applicable:
        chord_strategy = "modal_or_pedal_without_forced_function"
    elif record.harmony_understanding.valuable_weirdness:
        chord_strategy = "controlled_chromatic_color_motion"
    else:
        chord_strategy = "functional_or_quasi_functional_direction"
    avoid = ["random unprepared semitone stacks", "over-dense low-register clusters"]
    preserve = []
    if record.harmony_understanding.valuable_weirdness:
        preserve.append("intentional chromatic color tones that resolve or repeat motif")
    if record.motif_understanding.motif_cell_detected:
        preserve.append("motif cell and transformed repetitions")
    return GenerationHooks(
        target_tempo_range=[low, high],
        target_key_or_mode=record.harmony_understanding.center_hint or "ambiguous_mode_allowed",
        chord_movement_strategy=chord_strategy,
        bass_motion_strategy="step_and_fifth_anchors_with_passing" if record.voice_leading_score >= 0.35 else "root_pedal_support",
        voice_leading_strategy="favor_common_tones_and_step_resolutions",
        motif_development_strategy="repeat-transform-contract" if record.motif_reusability_score >= 0.4 else "short-call-response-cells",
        rhythm_strategy="pocket_first_with_syncopation_windows" if record.groove_value_score >= 0.4 else "sparse_grid_with_accent_lifts",
        form_strategy=form_strategy,
        texture_strategy="layered_atmosphere_with_clear_roles" if record.texture_value_score >= 0.4 else "minimal_texture_roles",
        avoid_list=avoid,
        preserve_list=preserve,
        tension_curve=_curve(record.harmonic_interest_score),
        density_curve=_curve(record.texture_value_score),
        confidence=clamp01((record.generation_usefulness_score + record.transcription_reliability_score) / 2.0),
        source_records_used=[record.item_id],
    )


def to_generation_profile_row(profile_name: str, source_records: list[MusicTheoryUnderstandingRecord]) -> dict:
    if not source_records:
        return {
            "profile_name": profile_name,
            "target_tempo_range": [70, 90],
            "target_key_or_mode": "ambiguous_mode_allowed",
            "chord_movement_strategy": "modal_or_pedal_without_forced_function",
            "bass_motion_strategy": "root_pedal_support",
            "voice_leading_strategy": "minimize_large_leaps",
            "motif_development_strategy": "short-call-response-cells",
            "rhythm_strategy": "sparse_grid_with_accent_lifts",
            "form_strategy": "hybrid_form_with_anchor_refrain",
            "texture_strategy": "minimal_texture_roles",
            "avoid_list": ["random-note clusters"],
            "preserve_list": [],
            "tension_curve": [0.2, 0.3, 0.35, 0.3, 0.25],
            "density_curve": [0.2, 0.25, 0.3, 0.28, 0.24],
            "confidence": 0.2,
            "source_records_used": [],
        }
    hooks = [map_theory_to_generation_hooks(row) for row in source_records]
    first = hooks[0]
    avg_conf = sum(h.confidence for h in hooks) / len(hooks)
    return {
        "profile_name": profile_name,
        "target_tempo_range": first.target_tempo_range,
        "target_key_or_mode": first.target_key_or_mode,
        "chord_movement_strategy": first.chord_movement_strategy,
        "bass_motion_strategy": first.bass_motion_strategy,
        "voice_leading_strategy": first.voice_leading_strategy,
        "motif_development_strategy": first.motif_development_strategy,
        "rhythm_strategy": first.rhythm_strategy,
        "form_strategy": first.form_strategy,
        "texture_strategy": first.texture_strategy,
        "avoid_list": first.avoid_list,
        "preserve_list": first.preserve_list,
        "tension_curve": first.tension_curve,
        "density_curve": first.density_curve,
        "confidence": clamp01(avg_conf),
        "source_records_used": [row.item_id for row in source_records[:20]],
    }
