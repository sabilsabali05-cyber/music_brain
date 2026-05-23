from __future__ import annotations

from pathlib import Path

from features.texture_sound.composition_sound_plan_schema import (
    CompositionSoundPlan,
    InstrumentTextureRequest,
    MaxForLiveRoutingPlan,
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
from features.texture_sound.synplant_candidate_schema import (
    SynplantFeedbackRecord,
    SynplantGenerationSession,
    SynplantPatchCandidate,
    SynplantPatchSelection,
)


def test_sample_seed_schema_represents_local_sample_as_synplant_seed_candidate() -> None:
    profile = SampleSeedFeatureProfile(
        pitch_profile={"centroid_hz": 196.0},
        spectral_profile={"brightness": 0.41},
        transient_profile={"density": 0.22},
        noise_profile={"broadband_ratio": 0.18},
        harmonicity_profile={"harmonicity": 0.79},
    )
    record = SampleSeedRecord(
        sample_id="seed_bass_001",
        source_path="samples/library/bass/analog_seed.wav",
        duration_seconds=2.4,
        file_hash="sha256:abc123",
        feature_profile=profile,
        texture_tags=["warm", "analog", "low_end"],
        role_candidates=[SampleRoleCandidate(role="bass", confidence=0.93)],
        authorization_status="authorized",
        review_status="approved",
        embedding_refs=["emb://seed_bass_001"],
        analysis_refs=["analysis://seed_bass_001"],
    )
    query = SampleSearchQuery(
        query_id="q1",
        composition_id="song_01",
        track_role="bass",
        desired_texture_description="rounded low-end mono foundation",
    )
    candidate = SynplantSeedCandidate(
        sample_id=record.sample_id,
        source_path=record.source_path,
        track_role="bass",
        role_confidence=0.93,
        seed_score=0.89,
        fit_reason="Matches requested analog bass texture profile.",
        feature_snapshot=record.feature_profile,
    )
    result = SampleSearchResult(
        query_id=query.query_id,
        composition_id=query.composition_id,
        track_role=query.track_role,
        candidates=[candidate],
    )
    assert result.candidates[0].sample_id == "seed_bass_001"
    assert result.candidates[0].track_role == "bass"


def test_synplant_generation_session_supports_manual_human_in_the_loop() -> None:
    session = SynplantGenerationSession(
        session_id="syn_sess_1",
        composition_id="song_01",
        track_role="pad",
        requested_texture_description="airy choir-like bed",
        seed_sample_id="seed_pad_101",
        seed_audio_path="samples/library/pads/choir_seed.wav",
        generation_method="manual",
        session_operator="human",
    )
    assert session.generation_method == "manual"
    assert session.session_operator == "human"
    assert session.seed_sample_id == "seed_pad_101"


def test_patch_selection_stores_selected_candidate_and_feedback() -> None:
    candidate = SynplantPatchCandidate(
        session_id="syn_sess_2",
        candidate_id="cand_a",
        track_role="lead",
        seed_sample_id="seed_lead_01",
        seed_audio_path="samples/library/leads/seed.wav",
        synplant_patch_ref="synplant://patch/cand_a",
        rendered_audio_ref="renders/song_01/lead_cand_a.wav",
        candidate_rank=1,
        selected=True,
    )
    selection = SynplantPatchSelection(
        session_id="syn_sess_2",
        composition_id="song_01",
        track_role="lead",
        selected_candidate_id=candidate.candidate_id,
        selected=True,
        selection_reason="Best role fit with minimal masking against vocals.",
        selected_by="hybrid",
    )
    feedback = SynplantFeedbackRecord(
        session_id="syn_sess_2",
        candidate_id=candidate.candidate_id,
        composition_id="song_01",
        track_role="lead",
        selected=True,
        selection_reason=selection.selection_reason,
        human_rating=4.5,
        model_rating=4.2,
        fit_to_role_score=0.91,
        fit_to_mix_score=0.85,
        novelty_score=0.64,
    )
    assert selection.selected_candidate_id == "cand_a"
    assert feedback.selected is True
    assert feedback.human_rating is not None and feedback.model_rating is not None


def test_composition_sound_plan_maps_midi_role_texture_seed_synplant_and_routing() -> None:
    role = TrackSoundRole(
        track_id="trk_01",
        midi_part_id="midi_part_bass_01",
        track_role="bass",
        texture_request_id="tex_req_01",
    )
    request = InstrumentTextureRequest(
        texture_request_id="tex_req_01",
        track_role="bass",
        desired_texture_description="dark sustained sub-bass with soft attack",
    )
    seed_assignment = SampleSeedAssignment(
        assignment_id="seed_assign_01",
        track_id="trk_01",
        midi_part_id="midi_part_bass_01",
        track_role="bass",
        texture_request_id="tex_req_01",
        sample_search_query_id="query_01",
        seed_sample_id="seed_bass_42",
        seed_audio_path="samples/library/bass/seed_bass_42.wav",
        assignment_reason="Top match for low harmonic movement and stable envelope.",
    )
    patch_assignment = SynplantPatchAssignment(
        assignment_id="patch_assign_01",
        track_id="trk_01",
        midi_part_id="midi_part_bass_01",
        track_role="bass",
        texture_request_id="tex_req_01",
        seed_sample_id="seed_bass_42",
        synplant_session_id="syn_sess_42",
        synplant_candidate_id="cand_b",
        synplant_patch_ref="synplant://patch/cand_b",
        rendered_audio_ref="renders/song_01/bass_patch_cand_b.wav",
        selected_by="hybrid",
    )
    routing = MaxForLiveRoutingPlan(
        route_id="route_01",
        ableton_track_name="Bass Texture",
        track_id="trk_01",
        midi_part_id="midi_part_bass_01",
        audio_source_ref=patch_assignment.rendered_audio_ref,
        max_device_chain=["Max Instrument Rack", "Utility", "Saturator"],
        macro_targets={"Macro1": "filter_cutoff", "Macro2": "drive"},
    )
    plan = CompositionSoundPlan(
        composition_id="song_01",
        track_sound_roles=[role],
        texture_requests=[request],
        sample_seed_assignments=[seed_assignment],
        synplant_patch_assignments=[patch_assignment],
        max_for_live_routing_plan=[routing],
    )
    assert plan.track_sound_roles[0].midi_part_id == "midi_part_bass_01"
    assert plan.sample_seed_assignments[0].seed_sample_id == "seed_bass_42"
    assert plan.synplant_patch_assignments[0].synplant_patch_ref.startswith("synplant://")
    assert plan.max_for_live_routing_plan[0].audio_source_ref.endswith(".wav")


def test_no_schema_assumes_direct_synth_replication_without_sample_seed() -> None:
    session = SynplantGenerationSession(
        session_id="syn_sess_guard",
        composition_id="song_guard",
        track_role="texture_bed",
        requested_texture_description="slow evolving pad",
        seed_sample_id="seed_guard_01",
        seed_audio_path="samples/library/textures/seed_guard_01.wav",
    )
    patch_assignment = SynplantPatchAssignment(
        assignment_id="patch_guard",
        track_id="trk_guard",
        midi_part_id="midi_guard",
        track_role="texture_bed",
        texture_request_id="tex_guard",
        seed_sample_id="seed_guard_01",
        synplant_session_id="syn_sess_guard",
        synplant_candidate_id="cand_guard",
        synplant_patch_ref="synplant://patch/cand_guard",
        rendered_audio_ref="renders/song_guard/texture_bed.wav",
    )
    assert session.seed_sample_id
    assert patch_assignment.seed_sample_id


def test_docs_mention_seed_selection_and_human_model_ranking() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    architecture_doc = repo_root / "docs" / "SYNPLANT_SEED_SELECTION_ARCHITECTURE.md"
    training_doc = repo_root / "docs" / "SOUND_SELECTION_TRAINING_DATA_PLAN.md"
    architecture_text = architecture_doc.read_text(encoding="utf-8").lower()
    training_text = training_doc.read_text(encoding="utf-8").lower()
    assert "seed" in architecture_text and "selection" in architecture_text
    assert "human" in architecture_text and "model" in architecture_text and "rank" in architecture_text
    assert "role_to_sample_seed_retrieval" in training_text
    assert "synplant_candidate_ranking" in training_text
