from __future__ import annotations

import json
from pathlib import Path

from features.model_training.training_data_routing_policy import (
    feedback_record_can_train_preference,
    puredata_output_training_candidate,
    route_record_for_training,
)
from scripts.evaluate_personalized_training_readiness import (
    build_personalized_training_plan,
    evaluate_personalized_training_readiness,
)


def _subsystem_map():
    plan = build_personalized_training_plan()
    return {item.subsystem_id: item for item in plan.subsystems}


def test_all_major_subsystems_have_personalization_path() -> None:
    subsystems = _subsystem_map()
    expected = {
        "moonbeam",
        "musicbert",
        "midigpt",
        "text2midi",
        "texture_embedding",
        "synplant_seed_selector",
        "synplant_patch_ranker",
        "puredata_texture_planner",
        "ableton_arrangement_agent",
        "overall_agent_controller",
    }
    assert expected.issubset(set(subsystems.keys()))
    for key in expected:
        assert subsystems[key].user_data_personalization_path.strip()


def test_moonbeam_not_left_generic() -> None:
    moonbeam = _subsystem_map()["moonbeam"]
    assert "adapter" in moonbeam.user_data_personalization_path.lower() or "lora" in moonbeam.user_data_personalization_path.lower()
    assert moonbeam.first_trainable_objective is not None


def test_musicbert_not_left_generic() -> None:
    musicbert = _subsystem_map()["musicbert"]
    assert "rank" in musicbert.first_trainable_objective.description.lower()


def test_midigpt_not_left_generic() -> None:
    midigpt = _subsystem_map()["midigpt"]
    assert "groove" in midigpt.first_trainable_objective.description.lower()


def test_text2midi_not_left_generic() -> None:
    text2midi = _subsystem_map()["text2midi"]
    assert "prompt" in text2midi.first_trainable_objective.description.lower()


def test_synplant_models_inherit_source_restrictions() -> None:
    record = {
        "model_origin": "synplant",
        "derived_type": "synplant_patch",
        "seed_source_policy": "splice_production_only",
        "source_policy": "user_owned_training_candidate",
        "authorization_status": "approved_for_training",
    }
    decision = route_record_for_training(record)
    assert decision.status == "block"
    assert "seed_restriction_not_inherited" in decision.reason


def test_splice_blocked_from_training() -> None:
    record = {"source_type": "splice_pack", "authorization_status": "approved_for_training"}
    decision = route_record_for_training(record)
    assert decision.status == "block"


def test_user_feedback_can_train_preference_models() -> None:
    feedback = {"feedback_type": "workflow_feedback", "accepted": True}
    assert feedback_record_can_train_preference(feedback) is True


def test_no_subsystem_claims_training_has_happened() -> None:
    plan = build_personalized_training_plan()
    for target in plan.subsystems:
        assert "has happened" not in target.user_data_personalization_path.lower()


def test_readiness_report_marks_blocked_honestly(tmp_path: Path) -> None:
    json_path, _, payload = evaluate_personalized_training_readiness(tmp_path)
    assert json_path.exists()
    states = {row["subsystem_id"]: row["readiness_state"] for row in payload["subsystem_readiness"]}
    assert states["synplant_seed_selector"] in {"blocked", "conditioning_ready", "ranker_training_ready"}
    assert payload["model_training_has_occurred"] is False


def test_training_route_policy_excludes_unauthorized_data() -> None:
    record = {"authorization_status": "unknown"}
    decision = route_record_for_training(record)
    assert decision.status == "block"


def test_puredata_candidate_only_when_authorized() -> None:
    record = {
        "model_origin": "pure_data",
        "authorization_status": "approved_for_training",
        "source_policy": "user_owned_training_candidate",
    }
    assert puredata_output_training_candidate(record) is True
    bad = {
        "model_origin": "pure_data",
        "source_type": "splice_pack",
        "authorization_status": "approved_for_training",
    }
    assert puredata_output_training_candidate(bad) is False


def test_readiness_script_writes_expected_report_fields(tmp_path: Path) -> None:
    json_path, md_path, _ = evaluate_personalized_training_readiness(tmp_path)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert md_path.exists()
    assert payload["first_recommended_trainable_subsystem"] == "musicbert"
    assert payload["model_training_has_occurred"] is False
