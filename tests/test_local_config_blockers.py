from __future__ import annotations

import json
from pathlib import Path


def test_local_config_blockers_are_boolean_and_redacted() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    json_path = repo_root / "reports" / "integration" / "local_config_blockers.json"
    md_path = repo_root / "reports" / "integration" / "local_config_blockers.md"
    assert json_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    for key in (
        "local_render_config_present",
        "local_vst_registry_present",
        "reaper_configured",
        "reaper_executable_available",
        "instrument_vst_available",
        "chordpotion_configured",
        "chordpotion_available",
        "training_allowed_in_complete_pipeline",
    ):
        assert isinstance(payload[key], bool)

    blockers = payload.get("blockers", [])
    assert isinstance(blockers, list)
    assert blockers

    raw_text = json_path.read_text(encoding="utf-8") + "\n" + md_path.read_text(encoding="utf-8")
    assert "C:\\Users\\" not in raw_text
    assert "C:/Users/" not in raw_text
