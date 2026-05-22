from __future__ import annotations

from collections import Counter

RHYTHM_PHILOSOPHIES: dict[str, str] = {
    "cycle": "Rhythm as cycle (tala, sam/khali, return logic)",
    "timeline": "Rhythm as timeline/key (clave-like asymmetrical guide patterns)",
    "cross_rhythm": "Rhythm as layered time and cross-rhythm",
    "attention": "Rhythm as entrainment, expectation, and surprise",
    "everyday_life": "Rhythmanalysis (cyclical/linear, eurhythmia/arrhythmia)",
    "hierarchy": "Rhythm as hierarchical structure across time scales",
    "geometry": "Rhythm as circular geometry and rotational similarity",
    "gesture": "Rhythm as embodied gesture (attack/release, push/pull)",
}

RHYTHM_CONCEPTS: list[str] = [
    "cycle",
    "pulse",
    "meter",
    "timeline",
    "polyrhythm",
    "syncopation",
    "density",
    "gesture",
    "repetition",
    "call_response",
    "harmonic_rhythm",
    "social_ritual",
    "arrhythmia",
    "eurhythmia",
    "rubato",
    "groove",
    "motif",
    "return",
    "hierarchy",
    "geometry",
    "entrainment",
]

DETECTION_TARGETS: dict[str, list[str]] = {
    "cycle": ["cycle_length", "return_point", "phrase_resolution", "light_region"],
    "pulse": ["pulse_confidence", "grid_stability", "beat_alignment"],
    "meter": ["beat_grouping", "subdivision_family", "meter_consistency"],
    "timeline": ["asymmetrical_skeleton", "timeline_fit", "offbeat_anchor"],
    "polyrhythm": ["multi_grid_fit", "cross_rhythm_tension", "layered_pulse"],
    "syncopation": ["expectation_violation", "offbeat_displacement", "phase_tension"],
    "density": ["event_density", "burst_density", "sparse_spacing"],
    "gesture": ["velocity_accent_shape", "attack_curve", "push_pull_timing"],
    "repetition": ["motif_recurrence", "pattern_repeat_count", "loop_persistence"],
    "call_response": ["alternating_density", "sparse_dense_exchange", "phrase_response_gap"],
    "harmonic_rhythm": ["chord_change_rate", "root_motion_flow", "harmonic_loop"],
    "social_ritual": ["collective_arrival", "ritual_build", "sectional_energy_arc"],
    "arrhythmia": ["irregular_grid", "instability_spikes", "unexpected_spacing"],
    "eurhythmia": ["stable_groove", "coherence_between_layers", "settled_pulse"],
    "rubato": ["tempo_stretch", "timing_drift", "phrase_timing_elasticity"],
    "groove": ["entrainment_strength", "microtiming_shape", "pulse_body_lock"],
    "motif": ["token_pattern", "ioi_pattern", "accent_pattern"],
    "return": ["cyclic_return", "cadential_arrival", "loop_reentry"],
    "hierarchy": ["onset_level", "beat_level", "phrase_level", "section_level"],
    "geometry": ["circular_pattern_similarity", "rotation_equivalence", "evenness_score"],
    "entrainment": ["attention_lock", "pulse_stability", "predictive_match"],
}

FEATURE_TO_CONCEPT_MAP: dict[str, list[str]] = {
    "note_on_density_per_second": ["density", "gesture"],
    "burst_density_regions": ["density", "gesture", "social_ritual"],
    "sparse_regions": ["density", "call_response"],
    "syncopation_proxy_score": ["syncopation", "arrhythmia", "groove"],
    "estimated_pulse_seconds": ["pulse", "meter", "entrainment"],
    "estimated_grid_resolution_seconds": ["pulse", "meter"],
    "common_ioi_ratios": ["motif", "repetition", "geometry"],
    "common_ioi_seconds": ["motif", "repetition"],
    "velocity_accent_stats": ["gesture", "groove"],
    "inter_onset_interval_histogram": ["motif", "hierarchy"],
    "chord_change_count": ["harmonic_rhythm", "gesture"],
    "repeated_chord_score": ["cycle", "repetition", "harmonic_rhythm", "return"],
    "root_motion_intervals": ["harmonic_rhythm", "hierarchy"],
    "interval_class": ["harmonic_rhythm", "geometry"],
    "semitone_motion": ["harmonic_rhythm", "gesture"],
    "diatonic_step_proxy": ["harmonic_rhythm", "meter"],
    "fifth_motion_proxy": ["harmonic_rhythm", "cycle"],
    "repeated_root": ["cycle", "return", "harmonic_rhythm"],
}

TAG_TO_CONCEPT_MAP: dict[str, list[str]] = {
    "dense_region": ["density", "gesture"],
    "dense_activity": ["density", "gesture", "social_ritual"],
    "sparse_region": ["density", "call_response"],
    "sparse_activity": ["density", "call_response"],
    "repeated_chord_vamp_candidate": ["cycle", "repetition", "harmonic_rhythm", "return"],
    "irregular_groove_candidate": ["arrhythmia", "groove", "pulse"],
    "steady_grid_candidate": ["pulse", "meter", "entrainment", "eurhythmia"],
    "repeated_rhythm_motif": ["motif", "repetition", "cycle"],
    "recurring_accent_pattern": ["motif", "gesture", "groove"],
    "dense_burst_pattern": ["density", "gesture", "social_ritual"],
    "sparse_call_response_candidate": ["call_response", "density", "hierarchy"],
    "triplet_grid_candidate": ["meter", "timeline", "geometry"],
    "straight_grid_candidate": ["meter", "pulse", "eurhythmia"],
    "rhythm_family_tresillo_candidate": ["timeline", "cycle", "motif"],
    "rhythm_family_clave_candidate": ["timeline", "cycle", "return"],
    "rhythm_family_backbeat_candidate": ["meter", "groove", "entrainment"],
    "rhythm_family_shuffle_candidate": ["meter", "groove", "gesture"],
    "rhythm_family_twelve_eight_gospel_candidate": ["meter", "social_ritual", "groove"],
    "rhythm_family_dembow_candidate": ["timeline", "cycle", "social_ritual"],
    "rhythm_family_boom_bap_candidate": ["groove", "meter", "gesture"],
    "rhythm_family_trap_subdivision_candidate": ["density", "gesture", "groove"],
    "rhythm_family_vamp_cycle_candidate": ["cycle", "repetition", "harmonic_rhythm", "return"],
}

CONCEPT_TO_PHILOSOPHY: dict[str, list[str]] = {
    "cycle": ["cycle", "everyday_life", "hierarchy"],
    "return": ["cycle", "hierarchy"],
    "pulse": ["attention", "hierarchy"],
    "meter": ["hierarchy", "attention", "geometry"],
    "timeline": ["timeline", "geometry"],
    "polyrhythm": ["cross_rhythm", "timeline"],
    "syncopation": ["attention", "cross_rhythm"],
    "density": ["gesture", "everyday_life"],
    "gesture": ["gesture", "attention"],
    "repetition": ["cycle", "geometry"],
    "call_response": ["everyday_life", "hierarchy"],
    "harmonic_rhythm": ["hierarchy", "cycle"],
    "social_ritual": ["everyday_life", "gesture"],
    "arrhythmia": ["everyday_life", "attention"],
    "eurhythmia": ["everyday_life", "attention"],
    "rubato": ["gesture", "attention"],
    "groove": ["attention", "gesture", "everyday_life"],
    "motif": ["geometry", "cycle"],
    "hierarchy": ["hierarchy"],
    "geometry": ["geometry"],
    "entrainment": ["attention", "everyday_life"],
}


def get_concepts_for_feature(feature_name: str) -> list[str]:
    return FEATURE_TO_CONCEPT_MAP.get(str(feature_name), [])


def get_detection_targets_for_concept(concept: str) -> list[str]:
    return DETECTION_TARGETS.get(str(concept), [])


def get_philosophy_sources_for_concept(concept: str) -> list[str]:
    return CONCEPT_TO_PHILOSOPHY.get(str(concept), [])


def _philosophies_for_concepts(concepts: list[str]) -> list[str]:
    sources: set[str] = set()
    for concept in concepts:
        sources.update(get_philosophy_sources_for_concept(concept))
    return sorted(sources)


def _targets_for_concepts(concepts: list[str]) -> list[str]:
    targets: set[str] = set()
    for concept in concepts:
        targets.update(get_detection_targets_for_concept(concept))
    return sorted(targets)


def annotate_tag_with_rhythm_concepts(tag_record: dict[str, object]) -> dict[str, object]:
    tag_name = str(tag_record.get("tag", ""))
    concepts = list(TAG_TO_CONCEPT_MAP.get(tag_name, []))
    if not concepts:
        evidence = tag_record.get("evidence", {})
        if isinstance(evidence, dict):
            for key in evidence:
                concepts.extend(get_concepts_for_feature(str(key)))
    concepts = sorted(set(concepts))
    tag_record["rhythm_concepts"] = concepts
    tag_record["philosophy_sources"] = _philosophies_for_concepts(concepts)
    tag_record["detection_targets"] = _targets_for_concepts(concepts)
    return tag_record


def annotate_feature_record_with_rhythm_concepts(feature_record: dict[str, object]) -> dict[str, object]:
    concepts: set[str] = set()
    features = feature_record.get("features", {})
    if isinstance(features, dict):
        for key in features.keys():
            concepts.update(get_concepts_for_feature(str(key)))
    granularity = str(feature_record.get("granularity", ""))
    if granularity == "rhythm_region":
        concepts.update(["hierarchy", "cycle"])
    if granularity == "chord_region":
        concepts.update(["harmonic_rhythm", "hierarchy"])
    if granularity in {"window", "segment"}:
        concepts.update(["hierarchy"])
    final_concepts = sorted(concepts)
    feature_record["rhythm_concepts"] = final_concepts
    feature_record["philosophy_sources"] = _philosophies_for_concepts(final_concepts)
    feature_record["detection_targets"] = _targets_for_concepts(final_concepts)
    return feature_record


def concept_count(records: list[dict[str, object]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for item in records:
        values = item.get("rhythm_concepts", [])
        if not isinstance(values, list):
            continue
        for value in values:
            counter[str(value)] += 1
    return dict(counter)


def philosophy_count(records: list[dict[str, object]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for item in records:
        values = item.get("philosophy_sources", [])
        if not isinstance(values, list):
            continue
        for value in values:
            counter[str(value)] += 1
    return dict(counter)
