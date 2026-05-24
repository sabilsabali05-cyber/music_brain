from __future__ import annotations

from features.concept_to_composition.concept_schema import SectionPlanItem, SongConceptBrief, TempoRange


def test_song_concept_brief_schema_accepts_required_fields() -> None:
    brief = SongConceptBrief(
        title="Test",
        short_description="desc",
        emotional_core="core",
        narrative_arc="arc",
        perspective="pov",
        scene_or_image="scene",
        energy_curve=[0.2, 0.4, 0.8],
        tension_curve=[0.1, 0.5, 0.6],
        density_curve=[0.2, 0.3, 0.5],
        tempo_range=TempoRange(min_bpm=90, max_bpm=110),
        key_or_mode_preference="A minor",
        harmony_strategy="functional",
        chord_movement_strategy="stepwise",
        bass_strategy="rooted",
        melody_strategy="singable",
        rhythm_strategy="sparse",
        texture_strategy="layered",
        arrangement_strategy="arc",
        section_plan=[SectionPlanItem(name="intro", bars=8, intent="set"), SectionPlanItem(name="verse", bars=8, intent="build"), SectionPlanItem(name="outro", bars=8, intent="resolve")],
        motifs_to_try=["falling third"],
        avoid_patterns=["random leaps"],
        preserve_patterns=["singable top line"],
        weirdness_policy="controlled",
        vocal_space_policy="protect center",
        reference_influence_policy="vibe only",
        generation_seed=1234,
        confidence=0.8,
        unresolved_questions=[],
    )
    assert brief.title == "Test"
    assert brief.tempo_range.min_bpm == 90
