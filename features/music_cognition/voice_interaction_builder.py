from __future__ import annotations

from typing import Any

from features.music_cognition.voice_interaction_schema import (
    InteractionEvidence,
    VoiceInteractionGraph,
    VoiceNode,
    WitnessSource,
)


def build_voice_interaction_graph(
    *,
    graph_id: str,
    stems: list[dict[str, Any]] | None = None,
    events: list[dict[str, Any]] | None = None,
    witnesses: list[dict[str, Any]] | None = None,
) -> VoiceInteractionGraph:
    stem_rows = stems or []
    event_rows = events or []
    witness_rows = witnesses or []

    if not stem_rows or not event_rows:
        return VoiceInteractionGraph(
            status="planned_no_evidence",
            graph_generated=False,
            graph_id=graph_id,
            voices=[],
            interactions=[],
            witness_not_truth=True,
            witness_sources=[],
        )

    voice_nodes = [
        VoiceNode(
            node_id=str(row.get("node_id", row.get("stem_id", "voice"))),
            voice_name=str(row.get("voice_name", row.get("stem_id", "unknown_voice"))),
            stem_id=str(row.get("stem_id", "unknown_stem")),
            onset_events=[float(item) for item in row.get("onset_events", []) if isinstance(item, (int, float))],
            note_events=[str(item) for item in row.get("note_events", [])],
            confidence=float(row.get("confidence", 0.0)),
        )
        for row in stem_rows
        if isinstance(row, dict)
    ]

    witness_sources = [
        WitnessSource(
            model_id=str(row.get("model_id", "unknown_model")),
            witness_role=str(row.get("witness_role", "evidence_support")),
            confidence=float(row.get("confidence", 0.0)),
            witness_not_truth=True,
        )
        for row in witness_rows
        if isinstance(row, dict)
    ]

    interactions = [
        InteractionEvidence(
            source_event_id=str(row.get("source_event_id", "unknown_source")),
            target_event_id=str(row.get("target_event_id", "unknown_target")),
            interaction_type=str(row.get("interaction_type", "unknown_interaction")),
            confidence=float(row.get("confidence", 0.0)),
            rhythmic_lock=float(row["rhythmic_lock"]) if isinstance(row.get("rhythmic_lock"), (int, float)) else None,
            call_response_score=float(row["call_response_score"])
            if isinstance(row.get("call_response_score"), (int, float))
            else None,
            spectral_masking_score=float(row["spectral_masking_score"])
            if isinstance(row.get("spectral_masking_score"), (int, float))
            else None,
            harmony_support_score=float(row["harmony_support_score"])
            if isinstance(row.get("harmony_support_score"), (int, float))
            else None,
            melodic_contour_relation=(
                str(row.get("melodic_contour_relation")) if row.get("melodic_contour_relation") is not None else None
            ),
            density_relation=str(row.get("density_relation")) if row.get("density_relation") is not None else None,
            notes=[str(note) for note in row.get("notes", []) if isinstance(note, str)],
            witness_sources=witness_sources,
        )
        for row in event_rows
        if isinstance(row, dict)
    ]

    return VoiceInteractionGraph(
        status="planned_with_evidence",
        graph_generated=bool(voice_nodes and interactions),
        graph_id=graph_id,
        voices=voice_nodes,
        interactions=interactions,
        witness_not_truth=True,
        witness_sources=witness_sources,
    )
