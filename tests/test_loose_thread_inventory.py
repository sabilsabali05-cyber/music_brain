from __future__ import annotations

import json
from pathlib import Path


def test_loose_thread_inventory_schema_and_required_entries() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    json_path = repo_root / "reports" / "integration" / "loose_threads_inventory.json"
    md_path = repo_root / "reports" / "integration" / "loose_threads_inventory.md"
    assert json_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    items = payload.get("items", [])
    assert isinstance(items, list)
    assert items

    allowed = {"merged_candidate", "useful_unmerged", "blocked", "duplicate", "stale", "retire_candidate"}
    names = {item["name"] for item in items}
    assert "complete_pipeline_orchestrator" in names
    assert "local_config_files" in names

    for item in items:
        assert item["status"] in allowed
        for key in (
            "name",
            "path_or_branch",
            "status",
            "what_it_does",
            "command_uses_it",
            "privacy_risk",
            "generated_artifact_risk",
            "next_action",
        ):
            assert key in item
            assert str(item[key]).strip()

    md_text = md_path.read_text(encoding="utf-8")
    assert "Discovered Related Untracked/Modified Buckets" in md_text
