from __future__ import annotations

import json
from pathlib import Path

import scripts.create_reaper_project_from_selected_candidate as reaper_project_script


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def test_reaper_project_creation_routes_chordpotion_into_synplant(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path
    stems = root / "outputs" / "complete_song_v1" / "stems"
    stems.mkdir(parents=True, exist_ok=True)
    for stem in ("bass.mid", "skeleton.mid", "lead.mid", "texture.mid"):
        (stems / stem).write_bytes(b"MThd")
    (root / "outputs" / "complete_song_v1" / "transformed_harmony.mid").write_bytes(b"MThd")

    _write_json(
        root / "config" / "local_render_config.local.json",
        {
            "synplant_enabled": True,
            "preferred_synplant_plugin_id": "synplant2",
            "synplant_bass_preset": "Bass Motion",
            "preferred_chordpotion_plugin_id": "chordpotion_midi_fx",
        },
    )
    _write_json(
        root / "config" / "local_vst_registry.local.json",
        {
            "registry_source": "test",
            "plugins": [
                {"plugin_id": "synplant2", "display_name": "Synplant 2", "category": "synth", "available": True},
                {"plugin_id": "chordpotion_midi_fx", "display_name": "ChordPotion", "category": "midi_fx", "available": True},
            ],
        },
    )

    monkeypatch.setattr(reaper_project_script, "ROOT_DIR", root)
    monkeypatch.setattr(reaper_project_script, "PROJECT_DIR", root / "outputs" / "reaper_projects" / "complete_song_v1")
    monkeypatch.setattr(
        reaper_project_script,
        "PROJECT_PATH",
        root / "outputs" / "reaper_projects" / "complete_song_v1" / "complete_song_v1.RPP",
    )
    monkeypatch.setattr(reaper_project_script, "REPORT_JSON", root / "reports" / "local_rendering" / "reaper_project_creation.json")
    monkeypatch.setattr(reaper_project_script, "REPORT_MD", root / "reports" / "local_rendering" / "reaper_project_creation.md")

    project_path, payload = reaper_project_script.create_reaper_project()
    assert project_path.exists()
    assert payload["reaper_project_created"] is True
    assert payload["chordpotion_can_route_into_synplant"] is True
    assert payload["synplant_is_not_composer"] is True

    project_text = project_path.read_text(encoding="utf-8")
    assert "midi_fx=chordpotion_midi_fx" in project_text
    assert "instrument=synplant2" in project_text
    assert "C:\\Users\\" not in project_text
    assert "C:/Users/" not in project_text
