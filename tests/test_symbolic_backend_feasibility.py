from __future__ import annotations

import json
from pathlib import Path

from scripts.research_symbolic_backend_feasibility import (
    build_feasibility_report,
    validate_feasibility_report,
    write_feasibility_report,
)


def test_feasibility_report_schema_validates(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    json_path, md_path = write_feasibility_report()
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert validate_feasibility_report(payload) == []


def test_unknown_fields_allowed_but_marked_unknown() -> None:
    payload = build_feasibility_report()
    backend = next(item for item in payload["backends"] if item["provider_id"] == "midigpt")
    backend["unknowns"]["extra_integration_risk"] = "unknown"
    assert validate_feasibility_report(payload) == []


def test_no_backend_marked_usable_without_evidence() -> None:
    payload = build_feasibility_report()
    backend = payload["backends"][0]
    backend["usable_with_current_repo_state"] = True
    backend["evidence"] = []
    errors = validate_feasibility_report(payload)
    assert any("cannot be marked usable without evidence" in error for error in errors)


def test_required_backends_present_in_report() -> None:
    payload = build_feasibility_report()
    providers = {item["provider_id"] for item in payload["backends"]}
    assert {"moonbeam", "midigpt", "text2midi", "musicbert"} <= providers
