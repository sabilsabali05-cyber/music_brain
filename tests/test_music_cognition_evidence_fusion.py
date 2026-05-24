from __future__ import annotations

import json
from pathlib import Path

from features.model_training.feedback_learning_policy import can_train_from_feedback
from features.music_cognition.voice_interaction_builder import build_voice_interaction_graph
from scripts import build_music_evidence_fusion_plan


def test_voice_interaction_graph_requires_real_evidence() -> None:
    graph = build_voice_interaction_graph(graph_id="g1", stems=[], events=[], witnesses=[])
    payload = graph.as_dict()
    assert payload["status"] == "planned_no_evidence"
    assert payload["graph_generated"] is False
    assert payload["interactions"] == []


def test_voice_interaction_graph_supports_required_relation_fields() -> None:
    graph = build_voice_interaction_graph(
        graph_id="g2",
        stems=[
            {
                "node_id": "v1",
                "voice_name": "lead",
                "stem_id": "lead_stem",
                "onset_events": [0.1, 0.5],
                "note_events": ["C4", "D4"],
                "confidence": 0.8,
            },
            {
                "node_id": "v2",
                "voice_name": "response",
                "stem_id": "resp_stem",
                "onset_events": [0.2, 0.6],
                "note_events": ["E4", "G4"],
                "confidence": 0.7,
            },
        ],
        events=[
            {
                "source_event_id": "v1_e1",
                "target_event_id": "v2_e1",
                "interaction_type": "call_response",
                "confidence": 0.72,
                "rhythmic_lock": 0.81,
                "call_response_score": 0.74,
                "spectral_masking_score": 0.2,
                "harmony_support_score": 0.68,
                "melodic_contour_relation": "contrary_motion",
                "density_relation": "supportive",
            }
        ],
        witnesses=[{"model_id": "yourmt3", "witness_role": "transcription_witness", "confidence": 0.51}],
    )
    payload = graph.as_dict()
    assert payload["graph_generated"] is True
    interaction = payload["interactions"][0]
    assert interaction["rhythmic_lock"] == 0.81
    assert interaction["call_response_score"] == 0.74
    assert interaction["spectral_masking_score"] == 0.2
    assert interaction["harmony_support_score"] == 0.68
    assert interaction["melodic_contour_relation"] == "contrary_motion"
    assert interaction["density_relation"] == "supportive"
    assert payload["witness_not_truth"] is True


def test_evidence_fusion_plan_defaults() -> None:
    plan = build_music_evidence_fusion_plan.build_evidence_fusion_plan().as_dict()
    assert plan["status"] == "planned"
    assert plan["fusion_performed"] is False
    assert plan["graph_generated"] is False
    assert plan["model_training_has_occurred"] is False


def test_feedback_learning_policy_training_exclusions_and_permissions() -> None:
    assert (
        can_train_from_feedback({"feedback_type": "ranker_feedback", "authorization_status": "authorized_for_training"})
        .trainable
        is True
    )
    assert can_train_from_feedback({"source_type": "transcription_witness", "authorization_status": "authorized_for_training"}).trainable is False
    assert can_train_from_feedback({"source_type": "separated_stem", "authorization_status": "authorized_for_training"}).trainable is False
    assert can_train_from_feedback({"source_type": "splice", "authorization_status": "authorized_for_training"}).trainable is False
    assert can_train_from_feedback({"source_type": "generated_midi", "human_reviewed": False, "authorization_status": "authorized_for_training"}).trainable is False
    assert can_train_from_feedback({"source_type": "generated_midi", "human_reviewed": True, "authorization_status": "authorized_for_training"}).trainable is True
    assert can_train_from_feedback({"source_type": "generated_midi", "authorization_status": "unknown"}).trainable is False


def test_evidence_fusion_plan_report_has_no_private_paths(tmp_path: Path) -> None:
    payload = build_music_evidence_fusion_plan.build_evidence_fusion_plan().as_dict()
    payload["created_at"] = "2026-01-01T00:00:00+00:00"
    json_path = tmp_path / "evidence_fusion_plan.json"
    md_path = tmp_path / "evidence_fusion_plan.md"
    from scripts.full_model_activation_common import write_report

    write_report(payload=payload, json_path=json_path, md_path=md_path, title="x", bullets=["no private paths"])
    text = json_path.read_text(encoding="utf-8") + md_path.read_text(encoding="utf-8")
    assert "C:/Users" not in text
    assert "C:\\Users" not in text
    json.loads(json_path.read_text(encoding="utf-8"))
