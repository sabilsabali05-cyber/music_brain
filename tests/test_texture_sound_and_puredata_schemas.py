from __future__ import annotations

from pathlib import Path

from features.generative_systems.puredata_schema import (
    PureDataConnection,
    PureDataControlMapping,
    PureDataGenerationRequest,
    PureDataObjectNode,
    PureDataParameter,
    PureDataPatchCandidate,
    PureDataPatchGraph,
    PureDataPatchTemplate,
)
from features.texture_sound.composition_sound_plan_schema import (
    CompositionSoundPlan,
    InstrumentTextureRequest,
    MaxForLiveRoutingPlan,
    PureDataSystemAssignment,
    SampleSeedAssignment,
    SynplantPatchAssignment,
    TrackSoundRole,
)
from features.texture_sound.sample_seed_schema import (
    SampleRoleCandidate,
    SampleSearchQuery,
    SampleSearchResult,
    SampleSeedFeatureProfile,
    SampleSeedRecord,
    SynplantSeedCandidate,
)
from features.texture_sound.synplant_candidate_schema import SynplantGenerationSession


def test_sample_seed_schema_represents_local_synplant_seed_candidate() -> None:
    profile = SampleSeedFeatureProfile(
        pitch_profile={"centroid_hz": 160.0},
        spectral_profile={"brightness": 0.37},
        transient_profile={"density": 0.21},
        noise_profile={"broadband_ratio": 0.14},
        harmonicity_profile={"harmonicity": 0.82},
    )
    seed = SampleSeedRecord(
        sample_id="seed_001",
        source_path="samples/library/analog/seed_001.wav",
        duration_seconds=1.9,
        file_hash="sha256:seed001",
        feature_profile=profile,
        texture_tags=["warm", "analog"],
        role_candidates=[SampleRoleCandidate(role="bass", confidence=0.91)],
        authorization_status="authorized",
        review_status="approved",
    )
    query = SampleSearchQuery(
        query_id="q1",
        composition_id="comp_1",
        track_role="bass",
        desired_texture_description="warm low-end texture",
    )
    candidate = SynplantSeedCandidate(
        sample_id=seed.sample_id,
        source_path=seed.source_path,
        track_role="bass",
        role_confidence=0.91,
        seed_score=0.88,
        feature_snapshot=seed.feature_profile,
    )
    result = SampleSearchResult(
        query_id=query.query_id,
        composition_id=query.composition_id,
        track_role=query.track_role,
        candidates=[candidate],
    )
    assert result.candidates[0].sample_id == "seed_001"
    assert result.candidates[0].source_path.endswith(".wav")


def test_synplant_session_supports_manual_generation() -> None:
    session = SynplantGenerationSession(
        session_id="syn_1",
        composition_id="comp_1",
        track_role="pad",
        requested_texture_description="airy evolving choir-like layer",
        seed_sample_id="seed_pad_1",
        seed_audio_path="samples/library/pads/seed_pad_1.wav",
        generation_method="manual",
    )
    assert session.generation_method == "manual"
    assert session.seed_sample_id == "seed_pad_1"


def test_puredata_schema_represents_template_based_patch() -> None:
    node = PureDataObjectNode(
        node_id="n1",
        object_name="metro",
        object_category="sequencer",
        inlets=2,
        outlets=1,
        parameters=[PureDataParameter(parameter_id="p1", name="rate", value_type="float", min_value=0.1, max_value=8.0)],
    )
    graph = PureDataPatchGraph(
        graph_id="g1",
        nodes=[node],
        sequencer_or_generator_type="euclidean",
        synthesis_or_effect_type="control",
        object_graph_summary="Template rhythm clock driving gate probabilities.",
    )
    template = PureDataPatchTemplate(
        template_id="tpl_euclid_1",
        display_name="Euclidean Trigger Template",
        patch_role="euclidean_rhythm_generator",
        template_patch_path="pd_templates/euclidean_trigger.pd",
        graph=graph,
        parameter_ranges={"rate": {"min": 0.1, "max": 8.0}},
        song_section_triggers=["verse", "chorus"],
    )
    assert template.template_patch_path.endswith(".pd")
    assert template.patch_role == "euclidean_rhythm_generator"


def test_puredata_schema_represents_midi_osc_audio_control_mappings() -> None:
    graph = PureDataPatchGraph(
        graph_id="g2",
        midi_inputs=["midi_in_1"],
        osc_inputs=["/tempo", "/scene"],
        audio_inputs=["inlet~_left", "inlet~_right"],
        audio_outputs=["outlet~_left", "outlet~_right"],
        random_sources=["noise~", "random"],
        sequencer_or_generator_type="markov",
        synthesis_or_effect_type="granular",
    )
    mapping_midi = PureDataControlMapping(
        mapping_id="m1",
        source="midi",
        source_ref="cc74",
        target_parameter_id="filter_cutoff",
        min_output=0.0,
        max_output=1.0,
    )
    mapping_osc = PureDataControlMapping(
        mapping_id="m2",
        source="osc",
        source_ref="/tempo",
        target_parameter_id="clock_rate",
    )
    _ = PureDataGenerationRequest(
        request_id="pd_req_1",
        composition_id="comp_1",
        track_role="fx",
        patch_role="spectral_freeze_effect",
        requested_texture_description="frozen shimmer tail",
        template_id="tpl_spectral_1",
        control_mappings=[mapping_midi, mapping_osc],
    )
    connection = PureDataConnection(
        source_node_id="n_src",
        source_outlet_index=0,
        target_node_id="n_tgt",
        target_inlet_index=0,
        connection_type="audio",
    )
    candidate = PureDataPatchCandidate(
        candidate_id="pd_cand_1",
        request_id="pd_req_1",
        composition_id="comp_1",
        track_role="fx",
        patch_role="spectral_freeze_effect",
        generated_patch_path="generated_pd/pd_cand_1.pd",
        graph_summary=graph,
        control_mappings=[mapping_midi, mapping_osc],
    )
    assert connection.connection_type == "audio"
    assert candidate.generated_patch_path.endswith(".pd")


def test_composition_sound_plan_assigns_synplant_or_puredata_to_track_role() -> None:
    role = TrackSoundRole(
        track_id="trk_1",
        midi_part_id="midi_1",
        track_role="drone",
        texture_request_id="tex_1",
    )
    request = InstrumentTextureRequest(
        texture_request_id="tex_1",
        track_role="drone",
        desired_texture_description="long unstable evolving drone",
    )
    seed_assignment = SampleSeedAssignment(
        assignment_id="seed_a",
        track_id="trk_1",
        midi_part_id="midi_1",
        track_role="drone",
        texture_request_id="tex_1",
        sample_search_query_id="q1",
        seed_sample_id="seed_drone_1",
        seed_audio_path="samples/library/drones/seed_drone_1.wav",
    )
    synplant_assignment = SynplantPatchAssignment(
        assignment_id="syn_a",
        track_id="trk_1",
        midi_part_id="midi_1",
        track_role="drone",
        texture_request_id="tex_1",
        seed_sample_id="seed_drone_1",
        synplant_session_id="syn_sess_1",
        synplant_candidate_id="syn_cand_1",
        synplant_patch_ref="synplant://patch/syn_cand_1",
        rendered_audio_ref="renders/comp_1/drone_syn.wav",
    )
    pd_assignment = PureDataSystemAssignment(
        assignment_id="pd_a",
        track_id="trk_1",
        midi_part_id="midi_1",
        track_role="drone",
        texture_request_id="tex_1",
        pd_request_id="pd_req_1",
        pd_candidate_id="pd_cand_1",
        pd_template_id="tpl_drone_1",
        generated_patch_path="generated_pd/pd_cand_1.pd",
        rendered_audio_refs=["renders/comp_1/drone_pd.wav"],
    )
    routing = MaxForLiveRoutingPlan(
        route_id="route_1",
        ableton_track_name="Drone",
        track_id="trk_1",
        midi_part_id="midi_1",
        audio_source_ref="renders/comp_1/drone_syn.wav",
        max_device_chain=["Max Rack", "Compressor"],
    )
    plan = CompositionSoundPlan(
        composition_id="comp_1",
        track_sound_roles=[role],
        texture_requests=[request],
        sample_seed_assignments=[seed_assignment],
        synplant_patch_assignments=[synplant_assignment],
        pure_data_system_assignments=[pd_assignment],
        max_for_live_routing_plan=[routing],
    )
    assert plan.synplant_patch_assignments[0].synplant_patch_ref.startswith("synplant://")
    assert plan.pure_data_system_assignments[0].generated_patch_path.endswith(".pd")


def test_no_schema_assumes_direct_sound_replication_without_seed_or_candidate() -> None:
    synplant_session = SynplantGenerationSession(
        session_id="syn_guard",
        composition_id="comp_guard",
        track_role="texture_bed",
        requested_texture_description="slow bed",
        seed_sample_id="seed_guard",
        seed_audio_path="samples/library/bed/seed_guard.wav",
    )
    pd_candidate = PureDataPatchCandidate(
        candidate_id="pd_guard",
        request_id="pd_req_guard",
        composition_id="comp_guard",
        track_role="texture_bed",
        patch_role="control_signal_generator",
        generated_patch_path="generated_pd/pd_guard.pd",
    )
    assert synplant_session.seed_sample_id
    assert pd_candidate.candidate_id


def test_docs_mention_synplant_seed_selection_puredata_and_max_ableton_routing() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    architecture_doc = (repo_root / "docs" / "SOUND_AND_GENERATIVE_SYSTEMS_ARCHITECTURE.md").read_text(
        encoding="utf-8"
    ).lower()
    training_doc = (repo_root / "docs" / "SOUND_SELECTION_AND_PD_TRAINING_DATA_PLAN.md").read_text(
        encoding="utf-8"
    ).lower()
    assert "synplant" in architecture_doc and "seed" in architecture_doc and "selection" in architecture_doc
    assert "pure data" in architecture_doc
    assert "max for live" in architecture_doc and "ableton" in architecture_doc
    assert "pd_patch_candidate_ranking" in training_doc
    assert "rendered_stem_feedback_prediction" in training_doc
