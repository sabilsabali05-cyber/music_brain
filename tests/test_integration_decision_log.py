from __future__ import annotations

import json
from pathlib import Path


def test_integration_decision_log_has_expected_decisions() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    json_path = repo_root / "reports" / "integration" / "integration_decision_log.json"
    md_path = repo_root / "reports" / "integration" / "integration_decision_log.md"
    assert json_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    decisions = payload.get("decisions", [])
    assert isinstance(decisions, list)
    assert decisions

    allowed = {"keep/wire", "experimental", "local-only", "retire", "postpone"}
    subsystems = {item["subsystem"] for item in decisions}
    assert "complete_song_orchestrator" in subsystems
    assert "cloud_activation_tasks" in subsystems

    for item in decisions:
        assert item["decision"] in allowed
        assert item["rationale"].strip()
        assert isinstance(item["evidence"], list) and item["evidence"]

    md_text = md_path.read_text(encoding="utf-8")
    assert "decision=`keep/wire`" in md_text
