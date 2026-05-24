from __future__ import annotations

from pathlib import Path

from scripts import build_voice_interaction_graph, plan_ableton_review_export_from_activation


def test_voice_interaction_graph_defaults_to_no_evidence() -> None:
    payload = build_voice_interaction_graph.build_graph_payload()
    assert payload["status"] == "planned_no_evidence"
    assert payload["graph_generated"] is False


def test_ableton_export_plan_defaults_to_planned_only_without_evidence(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"allow_ableton_export": false}', encoding="utf-8")
    payload = plan_ableton_review_export_from_activation.build_plan_payload(Path(manifest))
    assert payload["status"] == "planned_no_evidence"
    assert payload["export_performed"] is False
